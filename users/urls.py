from django.urls import path
from .views import UserRetrieveUpdateView, RegisterView
from rest_framework_simplejwt.views import TokenObtainPairView

app_name = 'users'

urlpatterns = [
    path('profile/', UserRetrieveUpdateView.as_view(), name='user-profile'),
    path('register/', RegisterView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
]