import json

from django.contrib.auth import authenticate
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .authentication import create_auth_token


def read_json_body(request):
    if not request.body:
        return {}

    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def get_user_display_name(user):
    name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
    return name or user.get_username()


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

    return JsonResponse({
        "token": create_auth_token(user),
        "user": {
            "id": str(user.pk),
            "username": user.get_username(),
            "name": get_user_display_name(user),
            "role": "admin" if user.is_staff else "user",
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        },
    })
