from django.conf import settings
from django.http import HttpResponse


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin")

        if request.method == "OPTIONS" and self._is_allowed_origin(origin):
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if self._is_allowed_origin(origin):
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type"

        return response

    def _is_allowed_origin(self, origin):
        return bool(origin and origin in settings.CORS_ALLOWED_ORIGINS)
