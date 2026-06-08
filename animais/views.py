import json
import logging
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.http.multipartparser import MultiPartParser, MultiPartParserError
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from userhandling.api.authentication import require_admin_user

from .models import Animal, AnimalImages
from .forms import AnimalForm, AnimalFotosForm

logger = logging.getLogger("general_logger")

SENSITIVE_LOG_FIELD_PARTS = ("authorization", "password", "secret", "token", "api_key")
MAX_LOG_VALUE_LENGTH = 200
ANIMAL_API_LIST_CACHE_KEY = "animal_api:animals:list:v1"
ANIMAL_API_DETAIL_CACHE_KEY_PREFIX = "animal_api:animals:detail:v1"

SUPPORTED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
GENERIC_IMAGE_CONTENT_TYPES = {"", "application/octet-stream"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


def get_animal_detail_cache_key(animal_id):
    return f"{ANIMAL_API_DETAIL_CACHE_KEY_PREFIX}:{animal_id}"


def invalidate_animal_api_cache(animal_id=None):
    cache.delete(ANIMAL_API_LIST_CACHE_KEY)

    if animal_id is not None:
        cache.delete(get_animal_detail_cache_key(animal_id))


class CloudinaryUploadError(Exception):
    def __init__(self, message, log_context=None):
        super().__init__(message)
        self.log_context = log_context or {}


def truncate_log_value(value):
    text = str(value)
    if len(text) <= MAX_LOG_VALUE_LENGTH:
        return text

    return f"{text[:MAX_LOG_VALUE_LENGTH]}..."


def is_sensitive_log_field(field_name):
    field_name = field_name.lower()
    return any(part in field_name for part in SENSITIVE_LOG_FIELD_PARTS)


def sanitize_log_payload(payload):
    if payload is None:
        return None

    sanitized_payload = {}
    for key, value in payload.items():
        if is_sensitive_log_field(key):
            sanitized_payload[key] = "[redacted]"
        elif isinstance(value, (list, tuple)):
            sanitized_payload[key] = [truncate_log_value(item) for item in value]
        elif isinstance(value, dict):
            sanitized_payload[key] = sanitize_log_payload(value)
        else:
            sanitized_payload[key] = truncate_log_value(value)

    return sanitized_payload


def summarize_uploaded_file(image_file):
    if not image_file:
        return None

    return {
        "name": Path(getattr(image_file, "name", "") or "").name,
        "content_type": getattr(image_file, "content_type", "") or "",
        "size": getattr(image_file, "size", None),
    }


def get_request_log_context(request, payload=None, image_file=None, extra=None):
    context = {
        "method": request.method,
        "path": request.get_full_path(),
        "content_type": request.content_type or "",
        "content_length": request.META.get("CONTENT_LENGTH", ""),
        "origin": request.headers.get("Origin", ""),
        "referer": request.headers.get("Referer", ""),
        "user_agent": request.headers.get("User-Agent", ""),
        "remote_addr": request.META.get("REMOTE_ADDR", ""),
        "has_authorization": bool(request.headers.get("Authorization")),
        "payload": sanitize_log_payload(payload),
        "image_file": summarize_uploaded_file(image_file),
    }

    if extra:
        context.update(extra)

    return context


def log_animal_api_request(request, payload=None, image_file=None, extra=None):
    logger.info(
        "Animal API request received: %s",
        json.dumps(get_request_log_context(request, payload, image_file, extra)),
    )


def log_animal_api_rejection(request, reason, payload=None, image_file=None, status=400, extra=None):
    context = get_request_log_context(
        request,
        payload,
        image_file,
        {
            "status": status,
            "reason": reason,
            **(extra or {}),
        },
    )
    logger.warning("Animal API request rejected: %s", json.dumps(context))


def animal_api_error_response(request, detail, status=400, payload=None, image_file=None, extra=None):
    log_animal_api_rejection(
        request,
        detail,
        payload=payload,
        image_file=image_file,
        status=status,
        extra=extra,
    )
    return JsonResponse({"detail": detail}, status=status)


class AnimalList(LoginRequiredMixin, TemplateView):
    def get(self, response):
        
        caes = Animal.objects.filter(tipo=Animal.DOG)
        gatos = Animal.objects.filter(tipo=Animal.CAT)
        
        animal_form = AnimalForm()
        
        context = {
            'caes' : caes,
            'gatos' : gatos,
            'animal_form': animal_form,
        }
        
        return render(response, 'animais/animais.html', context)

class AnimalDetails(LoginRequiredMixin, TemplateView):
    def get(self, response, animal_id):
        
        animal = get_object_or_404(Animal, id= animal_id)
        
        form = AnimalFotosForm()
        
        context = {
            'animal' : animal,
            'form' : form
        }
        
        return render(response, 'animais/partials/animal_modal.html', context)
    
    def post(self, response):
        
        form = AnimalForm(response.POST)
        if form.is_valid():
            animal = form.save()
            context = {
                'animal' : animal
            }
            return render(response, 'animais/partials/animal_avatar.html', context)
        
        logger.info(form.errors)
        return HttpResponse("Falha a salvar!")


def is_multipart_request(request):
    return bool(request.content_type and request.content_type.startswith("multipart/form-data"))


def parse_multipart_request(request):
    if request.method == "POST":
        return request.POST, request.FILES

    try:
        parser = MultiPartParser(
            request.META,
            request,
            request.upload_handlers,
            request.encoding,
        )
        return parser.parse()
    except MultiPartParserError as error:
        log_animal_api_rejection(
            request,
            "Invalid multipart body.",
            extra={"parser_error": truncate_log_value(error)},
        )
        return None, None


def read_animal_request_payload(request):
    if is_multipart_request(request):
        post_data, files = parse_multipart_request(request)

        if post_data is None or files is None:
            return None, None, "Invalid multipart body."

        return post_data.dict(), files.get("image_file"), None

    payload = read_json_body(request)
    if payload is None:
        return None, None, "Invalid JSON body."

    return payload, None, None


def validate_animal_image_file(image_file):
    if not image_file:
        raise CloudinaryUploadError("Image file is required.")

    if image_file.size == 0:
        raise CloudinaryUploadError(
            "Image file is empty.",
            {"image_size": image_file.size},
        )

    if image_file.size > settings.CLOUDINARY_MAX_IMAGE_BYTES:
        raise CloudinaryUploadError(
            "Image file is too large.",
            {
                "image_size": image_file.size,
                "max_image_bytes": settings.CLOUDINARY_MAX_IMAGE_BYTES,
            },
        )

    content_type = (getattr(image_file, "content_type", "") or "").lower()
    extension = Path(image_file.name or "").suffix.lower()

    has_supported_content_type = content_type in SUPPORTED_IMAGE_CONTENT_TYPES
    has_supported_extension = extension in SUPPORTED_IMAGE_EXTENSIONS
    has_generic_content_type = content_type in GENERIC_IMAGE_CONTENT_TYPES

    if content_type and not has_supported_content_type and not has_generic_content_type:
        raise CloudinaryUploadError(
            "Unsupported image type.",
            {"image_content_type": content_type, "image_extension": extension},
        )

    if extension and not has_supported_extension:
        raise CloudinaryUploadError(
            "Unsupported image type.",
            {"image_content_type": content_type, "image_extension": extension},
        )

    if not has_supported_content_type and not has_supported_extension:
        raise CloudinaryUploadError(
            "Unsupported image type.",
            {"image_content_type": content_type, "image_extension": extension},
        )


def upload_animal_image_to_cloudinary(image_file):
    validate_animal_image_file(image_file)

    cloudinary_settings = {
        "CLOUDINARY_CLOUD_NAME": settings.CLOUDINARY_CLOUD_NAME,
        "CLOUDINARY_API_KEY": settings.CLOUDINARY_API_KEY,
        "CLOUDINARY_API_SECRET": settings.CLOUDINARY_API_SECRET,
    }
    missing_settings = [
        setting_name
        for setting_name, setting_value in cloudinary_settings.items()
        if not setting_value
    ]
    if missing_settings:
        raise CloudinaryUploadError(
            "Cloudinary is not configured.",
            {"missing_settings": missing_settings},
        )

    try:
        import cloudinary.uploader as cloudinary_uploader
    except ImportError as error:
        raise CloudinaryUploadError(
            "Cloudinary SDK is not installed.",
            {"missing_dependency": "cloudinary"},
        ) from error

    try:
        upload_result = cloudinary_uploader.upload(
            image_file,
            resource_type="image",
            folder=settings.CLOUDINARY_ANIMAL_FOLDER,
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )
    except Exception as error:
        logger.exception("Cloudinary animal image upload failed")
        raise CloudinaryUploadError(
            "Image upload failed.",
            {"error_type": type(error).__name__},
        ) from error

    secure_url = upload_result.get("secure_url")
    if not secure_url:
        raise CloudinaryUploadError("Cloudinary did not return an image URL.")

    return secure_url


def serialize_animal(animal, request=None):
    images = [
        serialized_image
        for serialized_image in (
            serialize_animal_image(image, request)
            for image in animal.fotos.all().order_by("id")
        )
        if serialized_image["image_url"]
    ]
    image_urls = [image["image_url"] for image in images]

    return {
        "id": animal.id,
        "name": animal.name,
        "species": animal.tipo,
        "breed": animal.raca,
        "age": animal.idade,
        "gender": animal.gender,
        "description": animal.descricao,
        "image_url": image_urls[0] if image_urls else "",
        "image_urls": image_urls,
        "images": images,
        "medical_history": animal.medical_history,
        "vaccinations": animal.vaccinations,
        "admission_date": animal.admission_date or animal.last_update_date,
    }


def serialize_animal_image(image, request=None):
    return {
        "id": image.id,
        "image_url": image.get_url(request),
    }


def read_json_body(request):
    if not request.body:
        return {}

    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def apply_animal_payload(animal, payload):
    field_map = {
        "name": "name",
        "species": "tipo",
        "breed": "raca",
        "age": "idade",
        "gender": "gender",
        "description": "descricao",
        "medical_history": "medical_history",
        "vaccinations": "vaccinations",
    }

    for api_field, model_field in field_map.items():
        if api_field in payload:
            setattr(animal, model_field, payload[api_field])

    return animal


def get_image_urls_from_payload(payload):
    raw_urls = []

    if "image_url" in payload:
        raw_urls.append(payload.get("image_url"))

    image_urls = payload.get("image_urls")
    if isinstance(image_urls, list):
        raw_urls.extend(image_urls)
    elif image_urls:
        raw_urls.append(image_urls)

    images = payload.get("images")
    if isinstance(images, list):
        for image in images:
            if isinstance(image, dict):
                raw_urls.append(image.get("image_url") or image.get("url"))
            else:
                raw_urls.append(image)

    return [
        image_url.strip()
        for image_url in raw_urls
        if isinstance(image_url, str) and image_url.strip()
    ]


def add_image_urls_to_animal(animal, payload):
    for image_url in get_image_urls_from_payload(payload):
        AnimalImages.objects.get_or_create(
            animal=animal,
            image_url=image_url,
        )


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def animal_list_api(request):
    if request.method == "OPTIONS":
        return HttpResponse(status=204)

    if request.method == "GET":
        cached_animals = cache.get(ANIMAL_API_LIST_CACHE_KEY)
        if cached_animals is not None:
            return JsonResponse(cached_animals, safe=False)

        animals = Animal.objects.prefetch_related("fotos").all().order_by("id")
        serialized_animals = [serialize_animal(animal, request) for animal in animals]
        cache.set(
            ANIMAL_API_LIST_CACHE_KEY,
            serialized_animals,
            timeout=None,
        )
        return JsonResponse(serialized_animals, safe=False)

    if not require_admin_user(request):
        return animal_api_error_response(
            request,
            "Authentication credentials were not provided.",
            status=403,
        )

    payload, image_file, error = read_animal_request_payload(request)
    if error:
        return animal_api_error_response(request, error, status=400)

    log_animal_api_request(request, payload, image_file)

    try:
        if image_file:
            payload["image_url"] = upload_animal_image_to_cloudinary(image_file)

        animal = apply_animal_payload(Animal(), payload)
        animal.save()
        add_image_urls_to_animal(animal, payload)
    except CloudinaryUploadError as error:
        return animal_api_error_response(
            request,
            str(error),
            status=400,
            payload=payload,
            image_file=image_file,
            extra=error.log_context,
        )

    invalidate_animal_api_cache(animal.id)
    return JsonResponse(serialize_animal(animal, request), status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "PATCH", "DELETE", "OPTIONS"])
def animal_detail_api(request, animal_id):
    if request.method == "OPTIONS":
        return HttpResponse(status=204)

    if request.method == "GET":
        cache_key = get_animal_detail_cache_key(animal_id)
        cached_animal = cache.get(cache_key)
        if cached_animal is not None:
            return JsonResponse(cached_animal)

        animal = get_object_or_404(
            Animal.objects.prefetch_related("fotos"),
            id=animal_id,
        )
        serialized_animal = serialize_animal(animal, request)
        cache.set(
            cache_key,
            serialized_animal,
            timeout=None,
        )
        return JsonResponse(serialized_animal)

    animal = get_object_or_404(Animal, id=animal_id)

    if not require_admin_user(request):
        return animal_api_error_response(
            request,
            "Authentication credentials were not provided.",
            status=403,
            extra={"animal_id": animal_id},
        )

    if request.method == "DELETE":
        animal.delete()
        invalidate_animal_api_cache(animal_id)
        return HttpResponse(status=204)

    payload, image_file, error = read_animal_request_payload(request)
    if error:
        return animal_api_error_response(
            request,
            error,
            status=400,
            extra={"animal_id": animal_id},
        )

    log_animal_api_request(request, payload, image_file, extra={"animal_id": animal_id})

    try:
        if image_file:
            payload["image_url"] = upload_animal_image_to_cloudinary(image_file)

        apply_animal_payload(animal, payload)
        animal.save()
        add_image_urls_to_animal(animal, payload)
    except CloudinaryUploadError as error:
        return animal_api_error_response(
            request,
            str(error),
            status=400,
            payload=payload,
            image_file=image_file,
            extra={"animal_id": animal_id, **error.log_context},
        )

    invalidate_animal_api_cache(animal.id)
    return JsonResponse(serialize_animal(animal, request))


class AnimalImagens(LoginRequiredMixin, TemplateView):
    def post(self, response, animal_id):
        
        form = AnimalFotosForm(response.POST)
        
        if form.is_valid():
            animal = get_object_or_404(Animal, id= animal_id)
            
            AnimalImages.objects.create(
                animal = animal,
                image_url = form.cleaned_data['image_url']
            )
            form = AnimalFotosForm()
            
            context = {
                'form': form,
                'animal' : animal
            }
            return render(response, 'animais/partials/animal_modal_fotos.html', context)

        
        logger.info(form.errors)
        return HttpResponse("Falha a salvar!")
