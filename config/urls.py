from django.contrib import admin
from django.urls import include
from rest_framework.routers import DefaultRouter
from courses.views import (
    CourseViewSet,
    LessonViewSet,
    SubscriptionAPIView,
    LessonCompleteAPIView,
    UnsubscribeAPIView,
    LessonQuizAPIView,
    QuizSubmitAPIView,
)
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.urls import path
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static

schema_view = get_schema_view(
    openapi.Info(
        title="LingLoop API",
        default_version="v1",
        description=(
            "Backend API for the LingLoop "
            "speaking-practice application.\n\n"
            "Main speaking flow:\n"
            "1. Create a speaking attempt.\n"
            "2. Upload M4A audio directly to S3.\n"
            "3. Confirm the upload.\n"
            "4. Poll attempt detail until completed "
            "or failed.\n\n"
            "Authentication: JWT Bearer token."
        ),
    ),
    public=True,
    permission_classes=(
        permissions.AllowAny,
    ),
    authentication_classes=[],
)


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
        "api/",
        include(
            "speaking.urls",
            namespace="speaking",
        ),
    ),
    path(
        "api/courses/subscribe/", SubscriptionAPIView.as_view(), name="course-subscribe"
    ),
    path(
        "api/courses/unsubscribe/",
        UnsubscribeAPIView.as_view(),
        name="course-unsubscribe",
    ),
    path(
        "api/lessons/<uuid:lesson_id>/complete/",
        LessonCompleteAPIView.as_view(),
        name="lesson-complete",
    ),
    path(
        "api/lessons/<uuid:lesson_id>/quiz/",
        LessonQuizAPIView.as_view(),
        name="lesson-quiz",
    ),
    path(
        "api/quizzes/<uuid:quiz_id>/submit/",
        QuizSubmitAPIView.as_view(),
        name="quiz-submit",
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
    path("", lambda r: HttpResponse("все ок")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
