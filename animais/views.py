import json
import logging

from django.contrib.auth import authenticate, get_user_model
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import signing
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Animal, AnimalImages
from .forms import AnimalForm, AnimalFotosForm

logger = logging.getLogger("general_logger")
auth_signer = signing.TimestampSigner(salt="canil-gatil-api-token")


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


def serialize_animal(animal, request=None):
    image_url = animal.image_url

    if not image_url and animal.fotos.exists() and request:
        image_url = request.build_absolute_uri(animal.fotos.first().imagem.url)

    return {
        "id": animal.id,
        "name": animal.name,
        "species": animal.tipo,
        "breed": animal.raca,
        "age": animal.idade,
        "gender": animal.gender,
        "description": animal.descricao,
        "image_url": image_url,
        "medical_history": animal.medical_history,
        "vaccinations": animal.vaccinations,
        "admission_date": animal.admission_date or animal.last_update_date,
    }


def read_json_body(request):
    if not request.body:
        return {}

    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def get_token_user(request):
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Token "):
        return None

    token = authorization.removeprefix("Token ").strip()

    try:
        user_id = auth_signer.unsign(token)
    except signing.BadSignature:
        return None

    user_model = get_user_model()

    try:
        return user_model.objects.get(pk=user_id, is_active=True)
    except user_model.DoesNotExist:
        return None


def require_admin_user(request):
    user = get_token_user(request)
    return bool(user and user.is_staff)


def get_user_display_name(user):
    name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
    return name or user.get_username()


def apply_animal_payload(animal, payload):
    field_map = {
        "name": "name",
        "species": "tipo",
        "breed": "raca",
        "age": "idade",
        "gender": "gender",
        "description": "descricao",
        "image_url": "image_url",
        "medical_history": "medical_history",
        "vaccinations": "vaccinations",
    }

    for api_field, model_field in field_map.items():
        if api_field in payload:
            setattr(animal, model_field, payload[api_field])

    return animal


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def animal_list_api(request):
    if request.method == "OPTIONS":
        return HttpResponse(status=204)

    if request.method == "GET":
        animals = Animal.objects.all().order_by("id")
        return JsonResponse([serialize_animal(animal, request) for animal in animals], safe=False)

    if not require_admin_user(request):
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=403)

    payload = read_json_body(request)
    if payload is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)

    animal = apply_animal_payload(Animal(), payload)
    animal.save()

    return JsonResponse(serialize_animal(animal, request), status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "PATCH", "DELETE", "OPTIONS"])
def animal_detail_api(request, animal_id):
    if request.method == "OPTIONS":
        return HttpResponse(status=204)

    animal = get_object_or_404(Animal, id=animal_id)

    if request.method == "GET":
        return JsonResponse(serialize_animal(animal, request))

    if not require_admin_user(request):
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=403)

    if request.method == "DELETE":
        animal.delete()
        return HttpResponse(status=204)

    payload = read_json_body(request)
    if payload is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)

    apply_animal_payload(animal, payload)
    animal.save()

    return JsonResponse(serialize_animal(animal, request))


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def auth_token_api(request):
    if request.method == "OPTIONS":
        return HttpResponse(status=204)

    payload = read_json_body(request)
    if payload is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)

    user = authenticate(
        request,
        username=payload.get("username"),
        password=payload.get("password"),
    )

    if not user or not user.is_active:
        return JsonResponse({"detail": "Invalid credentials."}, status=400)

    token = auth_signer.sign(str(user.pk))

    return JsonResponse({
        "token": token,
        "user": {
            "id": str(user.pk),
            "username": user.get_username(),
            "name": get_user_display_name(user),
            "role": "admin" if user.is_staff else "user",
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        },
    })

class AnimalImagens(LoginRequiredMixin, TemplateView):
    def post(self, response, animal_id):
        
        form = AnimalFotosForm(response.POST, response.FILES)
        
        if form.is_valid():
            animal = get_object_or_404(Animal, id= animal_id)
            
            AnimalImages.objects.create(
                animal = animal,
                imagem = form.cleaned_data['imagem']
            )
            form = AnimalFotosForm()
            
            context = {
                'form': form,
                'animal' : animal
            }
            return render(response, 'animais/partials/animal_modal_fotos.html', context)

        
        logger.info(form.errors)
        return HttpResponse("Falha a salvar!")
