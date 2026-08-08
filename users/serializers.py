from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import Payment
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.utils.encoding import force_str
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode

User = get_user_model()


class UserSerializer(
    serializers.ModelSerializer
):
    avatar_url = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = User

        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "city",
            "avatar",
            "avatar_url",
            "date_joined",
        )

        read_only_fields = (
            "date_joined",
        )

    def get_avatar_url(
        self,
        obj,
    ):
        request = self.context.get(
            "request"
        )

        if obj.avatar:
            url = obj.avatar.url

            return (
                request.build_absolute_uri(
                    url
                )
                if request
                else url
            )

        return None


class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name", "phone")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ("user", "payment_date", "stripe_session_id", "stripe_checkout_url",)

    def validate(self, attrs):
        course = attrs.get("paid_course")
        lesson = attrs.get("paid_lesson")
        if not course and not lesson:
            raise serializers.ValidationError(
                "Укажи курс или урок для оплаты."
            )
        if course and lesson:
            raise serializers.ValidationError(
                "Нельзя указывать и курс, и урок одновременно."
            )
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(
    serializers.Serializer
):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True
    )

    def validate(self, attrs):
        try:
            uid = force_str(
                urlsafe_base64_decode(
                    attrs["uid"]
                )
            )

            user = User.objects.get(
                pk=uid,
                is_active=True,
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
            UnicodeDecodeError,
            User.DoesNotExist,
        ):
            raise serializers.ValidationError(
                "Invalid or expired reset link."
            )

        if not default_token_generator.check_token(
            user,
            attrs["token"],
        ):
            raise serializers.ValidationError(
                "Invalid or expired reset link."
            )

        try:
            validate_password(
                attrs["new_password"],
                user=user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "new_password": list(
                    error.messages
                ),
            }) from error

        attrs["user"] = user

        return attrs

    def save(self):
        user = self.validated_data["user"]

        user.set_password(
            self.validated_data["new_password"]
        )

        user.save(
            update_fields=["password"]
        )

        return user