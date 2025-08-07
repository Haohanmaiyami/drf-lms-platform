from rest_framework import serializers
from django.contrib.auth import get_user_model

from users.models import Payment

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'password', 'first_name', 'last_name', 'phone')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ("user", "payment_date")

    def validate(self, attrs):
        course = attrs.get("paid_course")
        lesson = attrs.get("paid_lesson")
        if not course and not lesson:
            raise serializers.ValidationError("Выберите либо оплаченный курс, либо урок.")
        if course and lesson:
            raise serializers.ValidationError("Нельзя указывать и курс, и урок одновременно.")
        return attrs