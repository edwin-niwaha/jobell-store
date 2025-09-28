from django import forms
from .models import Order
from django.core.exceptions import ValidationError
from phonenumbers import parse, is_valid_number, phonenumberutil


# class CheckoutForm(forms.Form):

#     first_name = forms.CharField(
#         max_length=50,
#         widget=forms.TextInput(
#             attrs={
#                 "class": "form-control",
#                 "placeholder": "First Name",
#             }
#         ),
#     )
#     last_name = forms.CharField(
#         max_length=50,
#         required=False,
#         widget=forms.TextInput(
#             attrs={
#                 "class": "form-control",
#                 "placeholder": "Last Name (optional)",
#             }
#         ),
#     )
#     email = forms.EmailField(
#         required=False,
#         widget=forms.EmailInput(
#             attrs={
#                 "class": "form-control",
#                 "placeholder": "Email (optional)",
#             }
#         ),
#     )

#     mobile = forms.CharField(
#         max_length=20,
#         required=False,
#         widget=forms.TextInput(
#             attrs={
#                 "class": "form-control",
#             }
#         ),
#         help_text="Enter your phone number including the country code (e.g., +12125552368).",
#     )

#     address = forms.CharField(
#         max_length=255,
#         required=False,
#         widget=forms.Textarea(
#             attrs={
#                 "class": "form-control",
#                 "placeholder": "Address",
#                 "rows": 2,
#             }
#         ),
#     )

#     def clean_mobile(self):
#         mobile = self.cleaned_data.get("mobile")

#         if mobile:
#             # Remove any spaces or hyphens before processing
#             mobile = mobile.replace(" ", "").replace("-", "")

#             try:
#                 # Parse the phone number using the phonenumbers library
#                 parsed_mobile = parse(mobile)

#                 # Check if the phone number is valid
#                 if not is_valid_number(parsed_mobile):
#                     raise ValidationError(
#                         "Invalid mobile number. Please enter a valid number in the format: +12125552368."
#                     )

#                 # Check if the phone number has a country code
#                 if not parsed_mobile.country_code:
#                     raise ValidationError(
#                         "Mobile number must include a country code. Please enter a valid number in the format: +12125552368."
#                     )

#             except phonenumberutil.NumberParseException:
#                 raise ValidationError(
#                     "Invalid mobile number format. Please enter a valid number in the format: +12125552368."
#                 )

#         return mobile


class CheckoutForm(forms.Form):
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "First Name",
            }
        ),
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Last Name (optional)",
            }
        ),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email (optional)",
            }
        ),
    )
    mobile = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g., +256123456789",
            }
        ),
    )
    address = forms.CharField(
        max_length=255,
        required=False,
        label="Shipping Address",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Shipping Address",
                "rows": 2,
            }
        ),
    )
    payment_method = forms.ChoiceField(
        choices=[("cod", "Cash on Delivery"), ("mobile", "Mobile Money")],
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="cod",
    )
    mobile_money_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g., +256123456789",
            }
        ),
        help_text="Enter your Mobile Money number including the country code (e.g., +256123456789).",
    )

    def clean_mobile(self):
        mobile = self.cleaned_data.get("mobile")

        if mobile:
            # Remove any spaces or hyphens before processing
            mobile = mobile.replace(" ", "").replace("-", "")

            try:
                # Parse the phone number using the phonenumbers library
                parsed_mobile = parse(mobile)

                # Check if the phone number is valid
                if not is_valid_number(parsed_mobile):
                    raise ValidationError(
                        "Invalid mobile number. Please enter a valid number in the format: +256123456789."
                    )

                # Check if the phone number has a country code
                if not parsed_mobile.country_code:
                    raise ValidationError(
                        "Mobile number must include a country code. Please enter a valid number in the format: +256123456789."
                    )

            except phonenumberutil.NumberParseException:
                raise ValidationError(
                    "Invalid mobile number format. Please enter a valid number in the format: +256123456789."
                )

        return mobile

    def clean_mobile_money_number(self):
        mobile_money_number = self.cleaned_data.get("mobile_money_number")
        payment_method = self.cleaned_data.get("payment_method")

        if payment_method == "mobile" and not mobile_money_number:
            raise ValidationError(
                "Mobile Money number is required for Mobile Money payment."
            )

        if mobile_money_number:
            # Remove any spaces or hyphens before processing
            mobile_money_number = mobile_money_number.replace(" ", "").replace("-", "")

            try:
                # Parse the phone number using the phonenumbers library
                parsed_number = parse(mobile_money_number)

                # Check if the phone number is valid
                if not is_valid_number(parsed_number):
                    raise ValidationError(
                        "Invalid Mobile Money number. Please enter a valid number in the format: +256123456789."
                    )

                # Check if the phone number has a country code
                if not parsed_number.country_code:
                    raise ValidationError(
                        "Mobile Money number must include a country code. Please enter a valid number in the format: +256123456789."
                    )

            except phonenumberutil.NumberParseException:
                raise ValidationError(
                    "Invalid Mobile Money number format. Please enter a valid number in the format: +256123456789."
                )

        return mobile_money_number

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get("payment_method")
        mobile_money_number = cleaned_data.get("mobile_money_number")

        # Additional cross-field validation
        if payment_method == "mobile" and not mobile_money_number:
            self.add_error(
                "mobile_money_number",
                "Mobile Money number is required for Mobile Money payment.",
            )

        return cleaned_data


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_status(self):
        status = self.cleaned_data.get("status")
        order = self.instance

        if order.status == status:
            raise forms.ValidationError(
                "The selected status is already set for this order."
            )

        return status
