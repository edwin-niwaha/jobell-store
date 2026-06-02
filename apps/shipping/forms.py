from django import forms

from .models import DeliveryRate, PickupStation


class DeliveryRateForm(forms.ModelForm):
    class Meta:
        model = DeliveryRate
        fields = ["region", "city", "area", "fee", "estimated_days", "is_active"]
        widgets = {
            "region": forms.Select(attrs={"class": "form-select"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "area": forms.TextInput(attrs={"class": "form-control"}),
            "fee": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "estimated_days": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class PickupStationForm(forms.ModelForm):
    class Meta:
        model = PickupStation
        fields = [
            "name",
            "city",
            "area",
            "address",
            "phone",
            "opening_hours",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "area": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "opening_hours": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
