from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView, ListAPIView
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet
from config import settings
from .models import Payment
from .serializers import UserSerializer, PaymentSerializer
from .serializers import UserRegisterSerializer
from .services.stripe_service import create_price, create_product, create_checkout_session
from rest_framework.parsers import MultiPartParser, FormParser

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
        serializer.save(user=self.request.user)
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



