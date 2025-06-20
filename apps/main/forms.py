from django import forms
from .models import Testimonial, Subscriber


class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ["text", "author", "approved"]

    # Custom widgets
    text = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "maxlength": 200,
                "placeholder": "Enter testimonial text",
            }
        )
    )
    author = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter author name"}
        )
    )
    approved = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    def clean_text(self):
        text = self.cleaned_data.get("text")
        max_length = 200  # Set the maximum length here
        if len(text) > max_length:
            raise forms.ValidationError(f"Text cannot exceed {max_length} characters.")
        return text


class NewsletterForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"placeholder": "Enter your email", "class": "form-control"}
        ),
        error_messages={"unique": "This email is already subscribed."},
    )
    consent = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="By clicking this checkbox, you consent to receiving emails from Jobell Inc.",
    )

    class Meta:
        model = Subscriber
        fields = ["email"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if Subscriber.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already subscribed.")
        return email


class EmailForm(forms.Form):
    subject = forms.CharField(
        max_length=255, widget=forms.TextInput(attrs={"class": "form-control"})
    )
    message = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control"}))
