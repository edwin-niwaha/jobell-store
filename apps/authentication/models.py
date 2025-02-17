from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from phonenumber_field.modelfields import PhoneNumberField
import requests
from io import BytesIO
from cloudinary.uploader import upload
from cloudinary.models import CloudinaryField
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError

from django.db import models
from PIL import Image


# =================================== Profile Model  ===================================


class Profile(models.Model):
    ROLE_CHOICES = (
        ("administrator", "Administrator"),
        ("manager", "Manager"),
        ("staff", "Staff"),
        ("guest", "Guest"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default="guest")
    avatar = CloudinaryField("avatar", default="default.jpg")
    bio = models.TextField()
    tel = PhoneNumberField(
        max_length=16,
        null=True,
        blank=True,
        default="+12125552368",
        verbose_name="Telephone",
    )
    mobile = PhoneNumberField(
        max_length=16,
        null=True,
        blank=True,
        default="+12125552368",
        verbose_name="Mobile",
    )

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        if isinstance(self.avatar, CloudinaryField):
            # If the avatar is already a Cloudinary resource
            response = requests.get(self.avatar.url)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))

                # Resize if necessary
                if img.height > 100 or img.width > 100:
                    output = BytesIO()
                    img.thumbnail((100, 100))
                    img.save(output, format=img.format)
                    output.seek(0)

                    # Re-upload resized image to Cloudinary
                    upload_result = upload(output, folder="profile_images")
                    self.avatar = upload_result["public_id"]

        elif isinstance(self.avatar, InMemoryUploadedFile):
            # If a new file is being uploaded
            img = Image.open(self.avatar)

            # Resize if necessary
            if img.height > 100 or img.width > 100:
                output = BytesIO()
                img.thumbnail((100, 100))
                img.save(output, format=img.format)
                output.seek(0)

                # Upload resized image to Cloudinary
                upload_result = upload(output, folder="profile_images")
                self.avatar = upload_result["public_id"]

        super().save(*args, **kwargs)


# =================================== Contact Model  ===================================
class Contact(models.Model):
    name = models.CharField(max_length=100, verbose_name="Your Name")
    email = models.EmailField(verbose_name="Your Email")
    message = models.TextField(
        verbose_name="Message"
    )  # Use TextField for larger messages
    is_valid = models.BooleanField(default=False, verbose_name="Valid?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "User Feedback"
        db_table = "client_feedback"

    def __str__(self):
        return f"Feedback from {self.name} ({self.email})"

    def clean(self):
        # Validate email format
        email = self.email
        if email:
            validator = EmailValidator(message="Enter a valid email address.")
            try:
                validator(email)
            except ValidationError as e:
                raise ValidationError({"email": e.message})

        # Validate message length
        if len(self.message) > 100:
            raise ValidationError("Message cannot exceed 100 characters.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Calls clean() before saving to enforce validations
        super().save(*args, **kwargs)
