from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserRetrieveUpdateView,
    RegisterView,
    PaymentViewSet,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import path
from . import views
from users.views import password_reset_redirect

app_name = "users"

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("profile/", UserRetrieveUpdateView.as_view(), name="user-profile"),
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("reset-password/", password_reset_redirect, name="password-reset-page"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

urlpatterns += router.urls
