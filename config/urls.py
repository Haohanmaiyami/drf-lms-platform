from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from courses.views import CourseViewSet, LessonViewSet

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"lessons", LessonViewSet, basename="lesson")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("users.urls", namespace="users")),
    path("api/", include(router.urls)),
]
