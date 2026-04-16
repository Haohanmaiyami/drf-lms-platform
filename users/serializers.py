from rest_framework import serializers
from django.contrib.auth import get_user_model

from users.models import Payment

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

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
        )

    def get_avatar_url(self, obj):
        request = self.context.get("request")
        if obj.avatar:
            url = obj.avatar.url
            return request.build_absolute_uri(url) if request else url
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
