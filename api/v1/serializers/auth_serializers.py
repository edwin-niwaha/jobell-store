from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.authentication.models import DeviceToken


class UserSerializer(serializers.ModelSerializer):
    is_email_verified = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_email_verified",
            "date_joined",
        ]

    def get_is_email_verified(self, obj):
        return True


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class FirebaseGoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)


class DeviceTokenSerializer(serializers.ModelSerializer):
    token = serializers.CharField(max_length=512, validators=[])

    class Meta:
        model = DeviceToken
        fields = ["id", "token", "platform", "app", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]
