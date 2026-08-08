from decimal import Decimal
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView, ListAPIView
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet
from config import settings
from .models import Payment
from .serializers import (
    UserSerializer,
    PaymentSerializer,
    UserRegisterSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from .services.stripe_service import create_price, create_product, create_checkout_session
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import render
from django.http import HttpResponse
from .tasks import send_password_reset_email
from .throttles import (
    PasswordResetEmailThrottle,
    PasswordResetIPThrottle,
)

User = get_user_model()


class UserRetrieveUpdateView(RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self):
        return self.request.user


class RegisterView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]


class PaymentViewSet(ModelViewSet):
    queryset = Payment.objects.select_related("user", "paid_course", "paid_lesson")
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["paid_course", "paid_lesson", "method"]
    ordering_fields = ["payment_date"]
    ordering = ["-payment_date"]

    def perform_create(self, serializer):
        payment: Payment = serializer.save(user=self.request.user)


        if payment.method != Payment.Method.STRIPE:
            return

        title = payment.paid_course.name if payment.paid_course else payment.paid_lesson.title
        amount_cents = int(Decimal(payment.amount) * 100)

        product = create_product(title)
        price = create_price(
            product_id=product["id"],
            amount_cents=amount_cents,
            currency=settings.STRIPE_CURRENCY,
        )
        session = create_checkout_session(
            price_id=price["id"],
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
            customer_email=self.request.user.email or None,
        )

        payment.stripe_session_id = session["id"]
        payment.stripe_checkout_url = session["url"]
        payment.save(update_fields=["stripe_session_id", "stripe_checkout_url"])



class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [
        PasswordResetIPThrottle,
        PasswordResetEmailThrottle,
    ]

    @swagger_auto_schema(
        request_body=PasswordResetRequestSerializer
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        email = (
            serializer.validated_data["email"]
            .strip()
        )

        send_password_reset_email.delay(email)

        return Response(
            {
                "detail": (
                    "If this email exists, "
                    "a reset link has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=PasswordResetConfirmSerializer)
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )


def password_reset_redirect(request):
    return render(request, "reset_password.html")


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        request.user.delete()
        return Response(
            {"detail": "Account deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )