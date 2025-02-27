from django.db import models


class Testimonial(models.Model):
    text = models.TextField()
    author = models.CharField(max_length=255)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "main_testimonial"


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        db_table = "subscribers"

    def __str__(self):
        return self.email
