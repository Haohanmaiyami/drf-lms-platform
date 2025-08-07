from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from users.views import PaymentViewSet

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payments')

urlpatterns = [
    path("admin/", admin.site.urls),
    # payments
    path("api/", include(router.urls)),
    # courses
    path("api/", include(("courses.urls", "courses"), namespace="courses")),
    # users (профиль/регистрация и т.п.)
    path("api/users/", include("users.urls", namespace="users")),
]
