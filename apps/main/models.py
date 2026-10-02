from django.db import models
from django.db.models.functions import Lower


class Testimonial(models.Model):
    text = models.TextField()
    author = models.CharField(max_length=255)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "main_testimonial"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["approved", "created_at"], name="test_appr_cr_idx"),
        ]


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    consent = models.BooleanField(default=False, verbose_name="Email Consent")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        db_table = "subscribers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"], name="subscriber_email_idx"),
            models.Index(fields=["consent", "created_at"], name="sub_consent_cr_idx"),
        ]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="subscriber_email_ci_unique"),
        ]

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.email
