from django import forms
from .models import Customer
from django.core.exceptions import ValidationError
from phonenumbers import parse, is_valid_number, phonenumberutil


# =================================== customer form ===================================
class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["first_name", "last_name", "address", "email", "tel", "mobile"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "tel": forms.TextInput(
                attrs={
                    "placeholder": "Enter your telphone number (e.g., +12125552368)",
                    "class": "form-control",
                    "id": "phone-input",
                }
            ),
            "mobile": forms.TextInput(
                attrs={
                    "placeholder": "Enter your mobile number (e.g., +12125552368)",
                    "class": "form-control",
                    "id": "phone-input",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Enter your email address",
                    "class": "email-input",
                }
            ),
        }
        help_texts = {
            "tel": "Enter your telephone number including the country code (e.g., +12125552368).",
            "mobile": "Enter your phone number including the country code (e.g., +12125552368).",
        }

        def clean_tel(self):
            # Pass the 'tel' field value to the clean_phone method
            return self.clean_phone(self.cleaned_data.get("tel"))

        def clean_mobile(self):
            # Pass the 'mobile' field value to the clean_phone method
            return self.clean_phone(self.cleaned_data.get("mobile"))

        def clean_phone(self, phone):
            if phone:
                # Convert PhoneNumber object to string before processing
                phone = str(phone).replace(" ", "").replace("-", "")

                try:
                    # Parse the phone number using phonenumbers library
                    parsed_phone = parse(phone)

                    # Check if the phone number is valid
                    if not is_valid_number(parsed_phone):
                        raise ValidationError(
                            "Invalid phone number. Please enter a valid number in the format: +12125552368."
                        )

                    # Check if the phone number has a country code
                    if not parsed_phone.country_code:
                        raise ValidationError(
                            "Phone number must include a country code. Please enter a valid number in the format: +12125552368."
                        )

                except phonenumberutil.NumberParseException:
                    raise ValidationError(
                        "Invalid phone number format. Please enter a valid number in the format: +12125552368."
                    )

            return phone
