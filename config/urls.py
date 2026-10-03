from pathlib import Path

from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path
from django.views.defaults import page_not_found
from drf_spectacular.views import SpectacularSwaggerView

BASE_DIR = Path(__file__).resolve().parent.parent


def api_404(request, exception):
    if request.path.startswith("/api/"):
        return JsonResponse(
            {"error": {"code": "not_found", "message": "Not found."}},
            status=404,
        )
    return page_not_found(request, exception)


handler404 = api_404


def contract_schema(request):
    text = (BASE_DIR / "openapi.yaml").read_text()
    return HttpResponse(text, content_type="application/yaml; charset=utf-8")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", contract_schema, name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("catalog.urls")),
    path("api/v1/", include("commerce.urls")),
]
