from django import forms

from .models import CustomerAddress


class CustomerAddressForm(forms.ModelForm):
    class Meta:
        model = CustomerAddress
        fields = [
            "street_name",
            "city",
            "area",
            "region",
            "phone_number",
            "additional_telephone",
            "additional_information",
            "is_default",
        ]
        widgets = {
            "street_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Street, building, apartment",
                    "autocomplete": "street-address",
                }
            ),
            "city": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "address-level2"}
            ),
            "area": forms.TextInput(attrs={"class": "form-control"}),
            "region": forms.Select(attrs={"class": "form-select"}),
            "phone_number": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "tel"}
            ),
            "additional_telephone": forms.TextInput(attrs={"class": "form-control"}),
            "additional_information": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

