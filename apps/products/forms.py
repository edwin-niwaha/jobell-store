from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Category,
    Volume,
    ProductVolume,
    Product,
    ProductImage,
    PRODUCT_TYPE_CHOICES,
)
from apps.inventory.models import Inventory


# =================================== category form ===================================
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter category name"}
            ),
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter category description",
                }
            ),
        }
        labels = {
            "name": "Category Name",
            "description": "Description",
        }


# =================================== volume form ===================================
class VolumeForm(forms.ModelForm):
    class Meta:
        model = Volume
        fields = ["ml", "cost", "price", "image"]
        widgets = {
            "ml": forms.NumberInput(attrs={"class": "form-control"}),
        }
        labels = {
            "ml": "Volume in ML",
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        return image


# =================================== ProductVolumeForm form ===================================
class ProductVolumeForm(forms.ModelForm):
    MAX_IMAGE_SIZE_MB = 10

    class Meta:
        model = ProductVolume
        # fields = ["volume", "product_type", "cost", "price", "discount_value", "image"]
        fields = ["volume", "product_type", "discount_value"]
        widgets = {
            "volume": forms.Select(attrs={"class": "form-control"}),
            "product_type": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop("product", None)
        super().__init__(*args, **kwargs)
        # Dynamically populate the volume choices
        self.fields["volume"].queryset = Volume.objects.all().order_by("ml")

    def clean(self):
        cleaned_data = super().clean()
        volume = cleaned_data.get("volume")
        product_type = cleaned_data.get("product_type")

        # Check if a ProductVolume with the same product, volume, and product_type already exists
        if (
            ProductVolume.objects.filter(
                product=self.product, volume=volume, product_type=product_type
            )
            .exclude(id=self.instance.id)
            .exists()
        ):
            raise ValidationError(
                "Oops! This combination of volume and product type is already assigned to this product."
            )
        return cleaned_data

    def save(self, commit=True):
        product_volume = super().save(commit=False)
        if self.product:
            product_volume.product = self.product
        if commit:
            product_volume.save()
        return product_volume


# =================================== Inventory form ===================================
class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ["quantity", "low_stock_threshold"]
        widgets = {
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Enter stock quantity"}
            ),
            "low_stock_threshold": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter low stock threshold",
                }
            ),
        }
        labels = {
            "quantity": "Stock Quantity",
            "low_stock_threshold": "Low Stock Threshold",
        }


# =================================== product form ===================================
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "status",
            "category",
            "gender",
            "supplier",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter product name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter product description",
                    "rows": 3,
                }
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "supplier": forms.Select(attrs={"class": "form-control"}),
        }
        labels = {
            "name": "Product Name",
            "description": "Description",
            "status": "Status",
            "category": "Category",
            "gender": "Gender",
            "suppliers": "Suppliers",  # Label for the suppliers field
        }


# =================================== CHILD PROFILE ===================================
class ProductImageForm(forms.ModelForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = ProductImage
        fields = ["image"]

        labels = {
            "image": "Upload Product Image:",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].widget = forms.FileInput(attrs={"accept": "image/*"})

    def clean_picture(self):
        picture = self.cleaned_data.get("image")
        if picture and picture.size > 1500 * 1024:  # 1.5 MB
            raise forms.ValidationError("Image size should not exceed 1.5 MB.")
        return picture


# =================================== Volume Selection Form ===================================
class VolumeSelectionForm(forms.Form):
    volume = forms.ModelChoiceField(
        queryset=Volume.objects.all(),
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Select Volume",
    )
    product_type = forms.ChoiceField(
        choices=PRODUCT_TYPE_CHOICES,  # Choices for product type
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Select Product Type",
    )
