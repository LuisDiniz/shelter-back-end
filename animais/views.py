import json
import logging

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from userhandling.api.authentication import require_admin_user

from .models import Animal, AnimalImages
from .forms import AnimalForm, AnimalFotosForm

logger = logging.getLogger("general_logger")


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
        animals = Animal.objects.all().order_by("id")
        return JsonResponse([serialize_animal(animal, request) for animal in animals], safe=False)

    if not require_admin_user(request):
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=403)

    payload = read_json_body(request)
    if payload is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)

    animal = apply_animal_payload(Animal(), payload)
    animal.save()
    add_image_urls_to_animal(animal, payload)

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
    add_image_urls_to_animal(animal, payload)

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
