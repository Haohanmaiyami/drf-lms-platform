from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserRetrieveUpdateView, RegisterView, PaymentViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import path
from . import views

app_name = "users"

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("profile/", UserRetrieveUpdateView.as_view(), name="user-profile"),
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

urlpatterns += router.urls
