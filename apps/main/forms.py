from django import forms
from .models import Testimonial
from apps.products.models import Category


class ProductFilterForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        label="Category",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Min Price",
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Min Price",  # Placeholder text
                "class": "form-control",  # Bootstrap styling
                "step": "0.01",  # Allow decimal values
                "min": "0",  # Ensure value is non-negative
            }
        ),
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Max Price",
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Max Price",  # Placeholder text
                "class": "form-control",  # Bootstrap styling
                "step": "0.01",  # Allow decimal values
                "min": "0",  # Ensure value is non-negative
            }
        ),
    )
    search = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={"placeholder": "Search by product name", "class": "form-control"}
        ),
    )


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
