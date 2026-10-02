from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import password_validators_help_text_html
from django.core.exceptions import ValidationError
from django.db import transaction
from phonenumber_field.formfields import PhoneNumberField
from phonenumbers import is_valid_number, parse, phonenumberutil

from apps.customers.models import Customer

from .models import Contact, Profile


# =================================== Register  ===================================
class RegisterForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        autocomplete = {"first_name": "given-name", "last_name": "family-name", "username": "username", "email": "email", "password1": "new-password", "password2": "new-password", "tel": "tel", "mobile": "tel"}
        for name, field in self.fields.items():
            field.widget.attrs["autocomplete"] = autocomplete.get(name, "on")
            field.widget.attrs.pop("data-toggle", None)
            if name in {"tel", "mobile"}:
                field.widget.attrs.update({"inputmode": "tel", "placeholder": "+256 777 123456"})
        self.fields["email"].widget = forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email", "placeholder": "you@example.com"})
        self.fields["password1"].help_text = password_validators_help_text_html()
        self.fields["username"].widget.attrs.pop("autofocus", None)
        for name, label in {"password1": "Password", "password2": "Confirm password", "tel": "Telephone", "mobile": "Mobile number"}.items():
            self.fields[name].label = label

    # fields we want to include and customize in our form
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "First Name",
                "class": "form-control",
            }
        ),
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Last Name",
                "class": "form-control",
            }
        ),
    )
    username = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control",
            }
        ),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Email",
                "class": "form-control",
            }
        ),
    )
    password1 = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control",
                "data-toggle": "password",
                "id": "password1",
            }
        ),
    )
    password2 = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm Password",
                "class": "form-control",
                "data-toggle": "password",
                "id": "password2",
            }
        ),
    )
    # Add Phone Number Fields
    tel = PhoneNumberField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Telephone (e.g., +12125552368)",
                "class": "form-control phone-input",
                "id": "tel-input",
            }
        ),
    )
    mobile = PhoneNumberField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Mobile (e.g., +12125552368)",
                "class": "form-control phone-input",
                "id": "mobile-input",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "password1",
            "password2",
            "tel",
            "mobile",
        ]

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "This username is already taken. Please choose another."
            )
        return username

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email")
        user.first_name = self.cleaned_data.get("first_name")
        user.last_name = self.cleaned_data.get("last_name")

        # if commit:
        #     user.save()
        #     # Create a Customer instance
        #     Customer.objects.create(user=user)
        # return user

        if commit:
            user.save()
            # Create a Customer instance with additional fields
            Customer.objects.create(
                user=user,
                first_name=self.cleaned_data.get("first_name"),
                last_name=self.cleaned_data.get("last_name"),
                address=self.cleaned_data.get("address"),  # Ensure address is captured
                email=self.cleaned_data.get("email"),
                tel=self.cleaned_data.get("tel"),
                mobile=self.cleaned_data.get("mobile"),
            )
        return user

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


# =================================== Login  ===================================
class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"
        self.fields["password"].widget.attrs.pop("data-toggle", None)

    username = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control",
            }
        ),
    )
    password = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control",
                "data-toggle": "password",
                "id": "password",
                "name": "password",
            }
        ),
    )
    remember_me = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ["username", "password", "remember_me"]


# =================================== User Update  ===================================
class UpdateUserForm(forms.ModelForm):
    username = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        required=True, widget=forms.TextInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = ["username", "email"]


# =================================== Pofile Update  ===================================


class UpdateProfileForm(forms.ModelForm):
    avatar = forms.ImageField(
        widget=forms.FileInput(attrs={"class": "form-control-file"})
    )
    bio = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3})
    )

    class Meta:
        model = Profile
        fields = ["avatar", "bio"]
        widgets = {
            "role": forms.Select(attrs={"class": "form-control", "required": True}),
        }


# =================================== Pofile Update * ===================================


class UpdateProfileAllForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = [
            "role",
        ]
        widgets = {
            "role": forms.Select(attrs={"class": "form-control", "required": True}),
            # "branch": forms.Select(attrs={"class": "form-control", "required": True}),
        }


# =================================== Contact Form  ===================================
class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        exclude = ("is_valid",)
        widgets = {
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("Email field is required")
        return email

    def clean_message(self):
        message = self.cleaned_data.get("message")
        if not message:
            raise forms.ValidationError("Message field is required")
        return message
