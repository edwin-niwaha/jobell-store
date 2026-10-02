import json
import os

from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials
except ImportError:  # pragma: no cover - handled as configuration error at runtime
    firebase_admin = None
    firebase_auth = None
    credentials = None


class AuthService:
    def register(self, *, email, username, password, password_confirm):
        if password != password_confirm:
            raise ValidationError("Passwords do not match.")

        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with this username already exists.")

        return User.objects.create_user(username=username, email=email, password=password)

    def login(self, *, email, password):
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        username = user.get_username() if user else email
        user = authenticate(username=username, password=password)
        if not user:
            raise ValidationError("Invalid email or password.")
        return user

    def tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    def firebase_google_login(self, *, id_token):
        claims = self._verify_firebase_id_token(id_token)
        provider = claims.get("firebase", {}).get("sign_in_provider")
        if provider != "google.com":
            raise ValidationError("Firebase token is not from Google sign-in.")

        email = (claims.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("Firebase account did not provide an email address.")
        if claims.get("email_verified") is False:
            raise ValidationError("Google email address is not verified.")

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            username = self._unique_username(email.split("@")[0] or "jobell")
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=claims.get("name", "").split(" ")[0][:150],
            )
            user.set_unusable_password()
            user.save(update_fields=["password"])

        display_name = claims.get("name") or ""
        if display_name and not (user.first_name or user.last_name):
            parts = display_name.split(" ", 1)
            user.first_name = parts[0][:150]
            user.last_name = parts[1][:150] if len(parts) > 1 else ""
            user.save(update_fields=["first_name", "last_name"])

        return user

    def _verify_firebase_id_token(self, id_token):
        if firebase_admin is None:
            raise ValidationError("Firebase Admin SDK is not installed.")
        self._ensure_firebase_app()
        try:
            return firebase_auth.verify_id_token(id_token, check_revoked=True)
        except Exception as exc:
            raise ValidationError("Firebase token could not be verified.") from exc

    def _ensure_firebase_app(self):
        if firebase_admin._apps:
            return

        project_id = os.getenv("FIREBASE_PROJECT_ID")
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if service_account_json:
            cred = credentials.Certificate(json.loads(service_account_json))
        elif service_account_path:
            cred = credentials.Certificate(service_account_path)
        else:
            cred = credentials.ApplicationDefault()

        options = {"projectId": project_id} if project_id else None
        firebase_admin.initialize_app(cred, options)

    def _unique_username(self, base):
        User = get_user_model()
        normalized = "".join(ch for ch in base.lower() if ch.isalnum() or ch in {"_", "."})[:140] or "jobell"
        username = normalized
        suffix = 1
        while User.objects.filter(username__iexact=username).exists():
            suffix += 1
            username = f"{normalized[:140 - len(str(suffix))]}{suffix}"
        return username


auth_service = AuthService()
