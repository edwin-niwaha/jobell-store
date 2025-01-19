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
        fields = ["text", "author"]
        widgets = {
            "text": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "author": forms.TextInput(attrs={"class": "form-control"}),
        }
