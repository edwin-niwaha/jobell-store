from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from api.v1.responses import api_response
from api.v1.serializers.auth_serializers import (
    DeviceTokenSerializer,
    FirebaseGoogleLoginSerializer,
    LogoutSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.authentication.models import DeviceToken
from services.auth_service import auth_service


class AuthViewSet(ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = auth_service.register(**serializer.validated_data)
        except DjangoValidationError as exc:
            return api_response({}, str(exc), False, status.HTTP_400_BAD_REQUEST)
        return api_response(
            {"user": UserSerializer(user).data, "tokens": auth_service.tokens_for_user(user)},
            "Account created successfully",
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = auth_service.login(**serializer.validated_data)
        except DjangoValidationError as exc:
            return api_response({}, str(exc), False, status.HTTP_400_BAD_REQUEST)
        return api_response(
            {"user": UserSerializer(user).data, "tokens": auth_service.tokens_for_user(user)},
            "Logged in successfully",
        )

    @action(detail=False, methods=["post"], url_path="firebase/google")
    def firebase_google(self, request):
        serializer = FirebaseGoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = auth_service.firebase_google_login(**serializer.validated_data)
        except DjangoValidationError as exc:
            return api_response({}, str(exc), False, status.HTTP_400_BAD_REQUEST)
        return api_response(
            {"user": UserSerializer(user).data, "tokens": auth_service.tokens_for_user(user)},
            "Logged in with Google successfully",
        )

    @action(detail=False, methods=["get", "patch"], url_path="me", permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        if request.method == "PATCH":
            user = request.user
            for field in ["first_name", "last_name", "username"]:
                if field in request.data:
                    setattr(user, field, request.data[field])
            user.save()
        return api_response(UserSerializer(request.user).data)

    @action(detail=False, methods=["post"], url_path="logout", permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except Exception:
            return api_response({}, "Token could not be blacklisted", False, status.HTTP_400_BAD_REQUEST)
        return api_response({}, "Logged out successfully")

    @action(detail=False, methods=["post"], url_path="device-token", permission_classes=[permissions.IsAuthenticated])
    def device_token(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        device_token, _ = DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user": request.user,
                "platform": serializer.validated_data["platform"],
                "app": serializer.validated_data.get("app", "jobell-mobile"),
                "is_active": True,
            },
        )
        return api_response(DeviceTokenSerializer(device_token).data, "Device token registered")
