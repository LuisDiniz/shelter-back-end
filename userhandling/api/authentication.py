from django.contrib.auth import get_user_model
from django.core import signing


auth_signer = signing.TimestampSigner(salt="canil-gatil-api-token")


def create_auth_token(user):
    return auth_signer.sign(str(user.pk))


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
