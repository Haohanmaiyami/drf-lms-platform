from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from courses.views import CourseViewSet, LessonViewSet, SubscriptionAPIView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.urls import path
from django.http import HttpResponse

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=[],
)
swagger_settings = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
        }
    }
}


def payment_success(request):
    return HttpResponse("Оплата прошла успешно!")


def payment_cancel(request):
    return HttpResponse("Оплата отменена.")

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"lessons", LessonViewSet, basename="lesson")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("users.urls", namespace="users")),
    path(
        "api/courses/subscribe/", SubscriptionAPIView.as_view(), name="course-subscribe"
    ),
    path("api/", include(router.urls)),
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("success/", payment_success, name="payment_success"),
    path("cancel/", payment_cancel, name="payment_cancel"),
]
