from django import forms
from .models import Order
from django.core.exceptions import ValidationError
from phonenumbers import parse, is_valid_number, phonenumberutil

from apps.addresses.models import CustomerAddress
from apps.shipping.models import PickupStation


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
    saved_address = forms.ModelChoiceField(
        queryset=CustomerAddress.objects.none(),
        required=False,
        empty_label="Use a new address",
        label="Saved address",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "First Name",
                "autocomplete": "given-name",
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
                "autocomplete": "family-name",
            }
        ),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email (optional)",
                "autocomplete": "email",
            }
        ),
    )
    mobile = forms.CharField(
        max_length=20,
        required=True,
        label="Contact Phone",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g., +256123456789",
                "autocomplete": "tel",
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
                "autocomplete": "street-address",
            }
        ),
    )
    delivery_region = forms.ChoiceField(
        choices=CustomerAddress.Region.choices,
        required=False,
        label="Delivery Region",
        initial=CustomerAddress.Region.KAMPALA_AREA,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    delivery_city = forms.CharField(
        max_length=100,
        required=False,
        label="City",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    delivery_area = forms.CharField(
        max_length=100,
        required=False,
        label="Area",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    save_address = forms.BooleanField(
        required=False,
        label="Save this address for next time",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    shipping_method = forms.ChoiceField(
        choices=Order.SHIPPING_METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="delivery",
    )
    pickup_station = forms.ModelChoiceField(
        queryset=PickupStation.objects.none(),
        required=False,
        empty_label="Choose pickup station",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    payment_method = forms.ChoiceField(
        choices=[("cod", "Cash on Delivery"), ("mobile", "Mobile Money")],
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="cod",
    )
    mobile_money_number = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g., 0777337491",
                "autocomplete": "tel",
                "inputmode": "numeric",
                "maxlength": "10",
                "pattern": "0[0-9]{9}",
            }
        ),
        help_text="Enter your 10-digit Mobile Money number starting with 0.",
    )
    payment_evidence = forms.CharField(
        max_length=100,
        required=False,
        label="Payment evidence",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Transaction ID, reference code, or sender name",
                "autocomplete": "off",
            }
        ),
        help_text="Send the money first, then enter the transaction ID, reference code, or sender name here.",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["pickup_station"].queryset = PickupStation.objects.filter(
            is_active=True
        )
        if user and user.is_authenticated:
            self.fields["saved_address"].queryset = CustomerAddress.objects.filter(
                user=user
            )
        else:
            self.fields.pop("saved_address")
            self.fields.pop("save_address")

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
            mobile_money_number = mobile_money_number.strip()
            if (
                not mobile_money_number.isdigit()
                or len(mobile_money_number) != 10
                or not mobile_money_number.startswith("0")
            ):
                raise ValidationError(
                    "Invalid Mobile Money number format. Please enter a 10-digit number starting with 0."
                )

        return mobile_money_number

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get("payment_method")
        mobile_money_number = cleaned_data.get("mobile_money_number")
        payment_evidence = cleaned_data.get("payment_evidence")
        shipping_method = cleaned_data.get("shipping_method")
        pickup_station = cleaned_data.get("pickup_station")
        saved_address = cleaned_data.get("saved_address")

        # Additional cross-field validation
        if (
            payment_method == "mobile"
            and not mobile_money_number
            and not self.errors.get("mobile_money_number")
        ):
            self.add_error(
                "mobile_money_number",
                "Mobile Money number is required for Mobile Money payment.",
            )
        if payment_method == "mobile" and not payment_evidence:
            self.add_error(
                "payment_evidence",
                "Please enter the transaction ID, reference code, or sender name after sending Mobile Money.",
            )

        if shipping_method == "pickup":
            if not pickup_station:
                self.add_error("pickup_station", "Please choose a pickup station.")
        else:
            if not saved_address and not cleaned_data.get("address"):
                self.add_error("address", "Please enter a delivery address.")
            if not saved_address and not cleaned_data.get("delivery_region"):
                self.add_error("delivery_region", "Please choose a delivery region.")
            if not saved_address and not cleaned_data.get("delivery_city"):
                self.add_error("delivery_city", "Please enter a delivery city.")

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
