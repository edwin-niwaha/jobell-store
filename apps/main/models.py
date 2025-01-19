from django.db import models


class Testimonial(models.Model):
    text = models.TextField()
    author = models.CharField(max_length=255)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "main_testimonial"
