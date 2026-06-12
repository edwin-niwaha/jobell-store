from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Category,
    Volume,
    ProductVolume,
    Product,
    ProductImage,
    Review,
    PRODUCT_TYPE_CHOICES,
)
from apps.inventory.models import Inventory


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


# =================================== category form ===================================
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "image", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter category name"}
            ),
            "slug": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Leave blank to auto-generate",
                }
            ),
            "image": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "name": "Category Name",
            "slug": "Slug",
            "image": "Category Icon/Image",
            "is_active": "Active",
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

    def clean_ml(self):
        ml = self.cleaned_data["ml"]
        duplicate = Volume.objects.filter(ml=ml).exclude(pk=self.instance.pk).exists()
        if duplicate:
            raise ValidationError(
                f"{ml}ML already exists. Reuse the existing volume and set product-specific prices on the variant."
            )
        return ml

    def clean_image(self):
        image = self.cleaned_data.get("image")
        return image


# =================================== ProductVolumeForm form ===================================
class ProductVolumeForm(forms.ModelForm):
    MAX_IMAGE_SIZE_MB = 10

    class Meta:
        model = ProductVolume
        fields = [
            "volume",
            "product_type",
            "price",
            "unit_cost",
            "stock_quantity",
            "sku",
            "barcode",
            "variant_image",
        ]
        widgets = {
            "volume": forms.Select(attrs={"class": "form-control"}),
            "product_type": forms.Select(attrs={"class": "form-control"}),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "e.g. 25000",
                }
            ),
            "unit_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "e.g. 18000",
                }
            ),
            "stock_quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "placeholder": "Optional"}
            ),
            "sku": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional. Leave blank to auto-generate.",
                }
            ),
            "barcode": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Optional barcode"}
            ),
            "variant_image": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }
        labels = {
            "volume": "Volume / Bottle Size",
            "product_type": "Variant Type",
            "price": "Selling Price for this Variant",
            "unit_cost": "Cost Price for this Variant",
            "stock_quantity": "Stock Quantity",
            "sku": "SKU",
            "barcode": "Barcode",
            "variant_image": "Variant Image",
        }

    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop("product", None)
        super().__init__(*args, **kwargs)
        self.fields["volume"].queryset = Volume.objects.all().order_by("ml")
        self.fields["volume"].empty_label = "Select a shared volume"
        self.fields["volume"].label_from_instance = lambda volume: f"{volume.ml}ML"
        self.fields["price"].required = True
        self.fields["unit_cost"].required = True
        self.fields["stock_quantity"].required = False

    def clean(self):
        cleaned_data = super().clean()
        volume = cleaned_data.get("volume")
        product_type = cleaned_data.get("product_type")
        sku = cleaned_data.get("sku")
        barcode = cleaned_data.get("barcode")

        if self.product and volume and product_type:
            duplicate_qs = ProductVolume.objects.filter(
                product=self.product,
                volume=volume,
                product_type=product_type,
            ).exclude(id=self.instance.id)
            if duplicate_qs.exists():
                raise ValidationError(
                    f"{self.product.name} already has {product_type} - {volume.ml}ML. Edit that variant instead."
                )
        if sku and ProductVolume.objects.filter(sku=sku).exclude(id=self.instance.id).exists():
            raise ValidationError("This SKU is already assigned to another variant.")
        if barcode and ProductVolume.objects.filter(barcode=barcode).exclude(id=self.instance.id).exists():
            raise ValidationError("This barcode is already assigned to another variant.")
        return cleaned_data

    def save(self, commit=True):
        product_volume = super().save(commit=False)
        if self.product:
            product_volume.product = self.product
        if not product_volume.name or {"volume", "product_type"} & set(self.changed_data):
            product_volume.name = product_volume.variant_label
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
            "slug",
            "description",
            "status",
            "category",
            "gender",
            "supplier",
            "cost_price",
            "selling_price",
            "is_featured",
            "hero_image",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter product name"}
            ),
            "slug": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Leave blank to auto-generate",
                }
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
            "cost_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "selling_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "hero_image": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }
        labels = {
            "name": "Product Name",
            "slug": "Slug",
            "description": "Description",
            "status": "Status",
            "category": "Category",
            "gender": "Gender",
            "supplier": "Supplier",  # Label for the suppliers field
            "cost_price": "Default Cost Price",
            "selling_price": "Default Selling Price",
            "is_featured": "Featured",
            "hero_image": "Hero Image",
        }


# =================================== CHILD PROFILE ===================================
class ProductImageForm(forms.ModelForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = ProductImage
        fields = ["image", "alt_text", "is_default", "is_active", "sort_order"]

        labels = {
            "image": "Upload Product Image:",
            "alt_text": "Alt Text",
            "is_default": "Default Image",
            "is_active": "Active",
            "sort_order": "Sort Order",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].widget = forms.FileInput(
            attrs={"accept": "image/*", "class": "form-control", "data-image-preview-input": "true"}
        )
        for field_name in ["alt_text", "sort_order"]:
            self.fields[field_name].widget.attrs.update({"class": "form-control"})
        self.fields["is_default"].widget.attrs.update({"class": "form-check-input"})
        self.fields["is_active"].widget.attrs.update({"class": "form-check-input"})

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 1500 * 1024:
            raise forms.ValidationError("Image size should not exceed 1.5 MB.")
        return image


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


# =================================== Product Review Form ===================================


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "review_text"]

    rating = forms.ChoiceField(choices=[(i, f"{i} Stars") for i in range(1, 6)])
    review_text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}), required=True
    )
