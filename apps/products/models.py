from django.db import models
from django.contrib.auth.models import User
from django.forms import model_to_dict
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import Avg, Q
from apps.supplier.models import Supplier
from cloudinary.models import CloudinaryField
import cloudinary.uploader
import uuid

from .services import generate_unique_slug, generate_variant_sku, percentage_discount


def validate_image_size(value):
    limit = 1500 * 1024  # 1,500 KB (1.5 MB)
    if value.size > limit:
        raise ValidationError("Image size should not exceed 1.5 MB.")


# Define choices for product status
STATUS_CHOICES = [
    ("", "-- Choose status --"),
    ("ACTIVE", "Active"),
    ("INACTIVE", "Inactive"),
]

# Define choices for gender
GENDER_CHOICES = [
    ("", "-- Choose gender --"),
    ("Unisex", "Unisex"),
    ("Male", "Male"),
    ("Female", "Female"),
]

# Define choices for product type
PRODUCT_TYPE_CHOICES = [
    ("", "-- Choose variant type --"),
    ("Mini", "Mini"),
    ("Roll-On", "Roll-On"),
    ("Spray", "Spray"),
    ("Diffuser", "Diffuser"),
]


class Category(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Name",
        db_index=True,
    )
    slug = models.SlugField(max_length=140, blank=True, db_index=True)
    image = CloudinaryField(
        "category_image",
        folder="gocart/categories",
        transformation={
            "width": 800,
            "height": 800,
            "crop": "fill",
            "quality": "auto",
            "fetch_format": "auto",
        },
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "category"
        verbose_name_plural = "Categories"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="category_name_idx"),
            models.Index(fields=["slug"], name="category_slug_idx"),
            models.Index(fields=["is_active", "name"], name="category_active_name_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="unique_category_slug"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Category, self.name, instance=self)
        super().save(*args, **kwargs)

    @property
    def image_url(self) -> str | None:
        return self.image.url if self.image else None


class Volume(models.Model):
    ml = models.IntegerField(unique=True, verbose_name="Volume in ML")
    cost = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Cost Price"
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Selling Price"
    )
    image = CloudinaryField("image", blank=True, null=True)

    class Meta:
        db_table = "volume_details"
        ordering = ["ml"]  # Sort by volume in ascending order
        verbose_name = "Volume"
        verbose_name_plural = "Volumes"
        indexes = [
            models.Index(fields=["ml"], name="volume_ml_idx"),
            models.Index(fields=["price"], name="volume_price_idx"),
            models.Index(fields=["cost"], name="volume_cost_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.image and not str(self.image).startswith("http"):
            upload_result = cloudinary.uploader.upload(
                self.image.file, folder="product_volume_images"
            )
            self.image = upload_result["url"]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ml} ML (Cost: {self.cost}, Price: {self.price})"


class Product(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True
    )
    name = models.CharField(max_length=256, verbose_name="Product Name", db_index=True)
    slug = models.SlugField(max_length=280, blank=True, db_index=True)
    description = models.TextField(verbose_name="Product Description")
    status = models.CharField(
        choices=STATUS_CHOICES, max_length=10, verbose_name="Status"
    )
    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Category",
    )
    volumes = models.ManyToManyField(
        Volume, through="ProductVolume", related_name="products"
    )
    supplier = models.ForeignKey(
        Supplier,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Supplier",
    )
    gender = models.CharField(
        choices=GENDER_CHOICES,
        max_length=10,
        default="Unisex",
        verbose_name="Targeted Gender",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    is_featured = models.BooleanField(default=False, verbose_name="Is Featured")
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    hero_image = CloudinaryField("hero image", blank=True, null=True)

    class Meta:
        db_table = "product"
        indexes = [
            models.Index(fields=["name"], name="product_name_idx"),
            models.Index(fields=["slug"], name="product_slug_idx"),
            models.Index(fields=["uuid"], name="product_uuid_idx"),
            models.Index(fields=["status"], name="product_status_idx"),
            models.Index(fields=["category", "status"], name="product_category_status_idx"),
            models.Index(fields=["supplier", "status"], name="product_supplier_status_idx"),
            models.Index(fields=["status", "is_featured"], name="product_status_featured_idx"),
            models.Index(fields=["gender", "status"], name="product_gender_status_idx"),
            models.Index(fields=["created_at"], name="product_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="unique_product_slug"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Product, self.name, instance=self)
        if self.hero_image and not str(self.hero_image).startswith("http"):
            upload_result = cloudinary.uploader.upload(
                self.hero_image.file, folder="product_hero_images"
            )
            self.hero_image = upload_result["url"]
        super().save(*args, **kwargs)

    def to_json(self):
        item = model_to_dict(self)
        try:
            inventory_quantity = self.inventory.quantity
        except ObjectDoesNotExist:
            inventory_quantity = 0
        item.update(
            {
                "id": self.id,
                "text": self.name,
                "category": self.category.name if self.category else None,
                "quantity": inventory_quantity,
                "total_product": 0,
            }
        )
        return item

    @property
    def prefixed_id(self):
        return f"JBL{self.pk:03d}"

    @property
    def title(self):
        return self.name

    @property
    def is_active(self):
        return self.status == "ACTIVE"

    @property
    def variants(self):
        return self.productvolume_set.all()

    @property
    def active_variants(self):
        return self.productvolume_set.filter(is_active=True).order_by(
            "sort_order", "volume__ml", "product_type"
        )

    @property
    def base_price(self):
        first_variant = self.active_variants.first() or self.productvolume_set.first()
        if first_variant:
            return first_variant.effective_price
        return self.selling_price

    @property
    def cost_basis(self):
        first_variant = self.active_variants.first() or self.productvolume_set.first()
        if first_variant:
            return first_variant.effective_cost
        return self.cost_price

    @property
    def gross_profit_amount(self):
        if self.base_price is None or self.cost_basis is None:
            return None
        return self.base_price - self.cost_basis

    @property
    def gross_margin_percent(self):
        if not self.base_price or self.gross_profit_amount is None:
            return None
        return (self.gross_profit_amount / self.base_price) * 100

    @property
    def is_in_stock(self):
        return self.active_variants.filter(
            models.Q(stock_quantity__isnull=True) | models.Q(stock_quantity__gt=0)
        ).exists()

    @property
    def hero_image_url(self):
        if self.hero_image:
            return getattr(self.hero_image, "url", str(self.hero_image))
        return ""

    @property
    def primary_image(self):
        default_image = self.images.filter(is_active=True, is_default=True).first()
        return default_image or self.images.filter(is_active=True).order_by(
            "sort_order", "-created_at"
        ).first()

    @property
    def image_urls(self):
        urls = []
        if self.hero_image_url:
            urls.append(self.hero_image_url)
        urls.extend(
            image.image_url
            for image in self.images.filter(is_active=True).order_by(
                "sort_order", "-created_at"
            )
            if image.image_url
        )
        return urls

    @property
    def average_rating(self):
        value = self.reviews.filter(is_verified=True).aggregate(Avg("rating"))[
            "rating__avg"
        ]
        return round(value, 1) if value else None

    @property
    def total_reviews(self):
        return self.reviews.filter(is_verified=True).count()


class ProductVolume(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_type = models.CharField(
        choices=PRODUCT_TYPE_CHOICES,
        max_length=10,
        default="Spray",
        verbose_name="Type",
    )
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE)
    name = models.CharField(
        max_length=120,
        blank=True,
        help_text="Customer-facing variant name. Defaults to type and volume.",
    )
    sku = models.CharField(max_length=80, blank=True, db_index=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional selling price override for this product variant.",
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional cost override for this product variant.",
    )
    stock_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Leave blank to keep legacy untracked-stock behavior.",
    )
    max_quantity_per_order = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    color = models.CharField(
        max_length=60,
        blank=True,
        help_text="Optional color/shade variation, e.g. Black, Red, Gold.",
    )
    size = models.CharField(
        max_length=60,
        blank=True,
        help_text="Optional non-volume size variation, e.g. Small, Medium, Large.",
    )
    scent = models.CharField(
        max_length=80,
        blank=True,
        help_text="Optional scent/fragrance variation.",
    )
    barcode = models.CharField(max_length=80, blank=True, db_index=True)
    variant_image = CloudinaryField("variant image", blank=True, null=True)
    attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra variation attributes such as material, pack size, or label.",
    )

    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Discount Value",
    )

    class Meta:
        verbose_name = "Product Variation"
        verbose_name_plural = "Product Variations"
        ordering = ["sort_order", "volume__ml", "product_type", "name"]
        indexes = [
            models.Index(fields=["product", "is_active"], name="variant_product_active_idx"),
            models.Index(fields=["product", "volume", "product_type"], name="variant_product_combo_idx"),
            models.Index(fields=["sku"], name="variant_sku_idx"),
            models.Index(fields=["barcode"], name="variant_barcode_idx"),
            models.Index(fields=["product_type"], name="variant_type_idx"),
            models.Index(fields=["is_active", "stock_quantity"], name="variant_active_stock_idx"),
            models.Index(fields=["price"], name="variant_price_idx"),
            models.Index(fields=["sort_order"], name="variant_sort_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "volume", "product_type", "color", "size", "scent"],
                name="unique_product_variation",
            ),
            models.UniqueConstraint(
                fields=["sku"],
                condition=~Q(sku=""),
                name="unique_product_variation_sku",
            ),
            models.UniqueConstraint(
                fields=["barcode"],
                condition=~Q(barcode=""),
                name="uniq_variant_barcode",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.variant_label} (SKU: {self.sku or 'Pending'})"

    def clean(self):
        super().clean()
        if not self.product_id or not self.volume_id or not self.product_type:
            return

        duplicate = (
            ProductVolume.objects.filter(
                product_id=self.product_id,
                volume_id=self.volume_id,
                product_type=self.product_type,
            )
            .exclude(pk=self.pk)
            .exists()
        )
        if duplicate:
            raise ValidationError(
                {
                    "product_type": (
                        f"{self.product.name} already has "
                        f"{self.product_type} - {self.volume.ml}ML. "
                        "Edit that variant instead of adding another one."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if not self.name and self.volume_id:
            self.name = self.variant_label
        if not self.sku and self.product_id:
            self.sku = generate_variant_sku(self.product, self.variant_label, instance=self)
        if self.variant_image and not str(self.variant_image).startswith("http"):
            upload_result = cloudinary.uploader.upload(
                self.variant_image.file, folder="product_variant_images"
            )
            self.variant_image = upload_result["url"]
        super().save(*args, **kwargs)

    @property
    def variant_label(self):
        parts = []
        if self.product_type:
            parts.append(self.product_type)
        if self.volume_id:
            parts.append(f"{self.volume.ml}ML")
        for value in (self.color, self.size, self.scent):
            if value:
                parts.append(value)
        return " - ".join(parts) or self.name or "Variant"

    @property
    def image_url(self):
        if self.variant_image:
            return getattr(self.variant_image, "url", str(self.variant_image))
        if self.product_id and self.product.primary_image:
            return self.product.primary_image.image_url
        return self.product.hero_image_url if self.product_id else ""

    @property
    def effective_price(self):
        return self.price if self.price is not None else self.volume.price

    @property
    def effective_cost(self):
        return self.unit_cost if self.unit_cost is not None else self.volume.cost

    @property
    def selling_price(self):
        return self.effective_price

    @property
    def original_price(self):
        return self.effective_price

    @property
    def current_price(self):
        return self.get_discounted_price()

    @property
    def has_price_discount(self):
        return (
            self.discount_value
            and self.original_price is not None
            and self.current_price is not None
            and self.current_price < self.original_price
        )

    @property
    def cost_price(self):
        return self.effective_cost

    @property
    def stock(self):
        return self.available_quantity

    @stock.setter
    def stock(self, value):
        self.stock_quantity = value

    @property
    def is_stock_tracked(self):
        if self.stock_quantity is not None:
            return True
        if not self.product_id:
            return False
        try:
            self.product.inventory
        except ObjectDoesNotExist:
            return False
        return True

    @property
    def available_quantity(self):
        if self.stock_quantity is not None:
            return self.stock_quantity
        if not self.product_id:
            return 0
        try:
            inventory = self.product.inventory
        except ObjectDoesNotExist:
            return 0
        return inventory.quantity or 0

    @property
    def is_in_stock(self):
        return self.is_active and self.available_quantity > 0

    @property
    def gross_profit_amount(self):
        if self.effective_price is None or self.effective_cost is None:
            return None
        return self.effective_price - self.effective_cost

    @property
    def gross_margin_percent(self):
        if not self.effective_price or self.gross_profit_amount is None:
            return None
        return (self.gross_profit_amount / self.effective_price) * 100

    def apply_discount(self):
        """Return the current discounted price without mutating the shared Volume."""
        return self.get_discounted_price()

    def get_discounted_price(self):
        """Get the discounted price with a percentage discount applied."""
        return percentage_discount(self.effective_price, self.discount_value)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name="images", on_delete=models.CASCADE
    )
    # image = CloudinaryField("image", blank=True, null=True)
    image = CloudinaryField(
        "image",
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"]),
            validate_image_size,
        ],
        null=True,
        blank=True,
    )
    alt_text = models.CharField(max_length=180, blank=True)
    is_default = models.BooleanField(default=False, verbose_name="Is Default")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")

    class Meta:
        db_table = "product_image"
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ["sort_order", "-created_at"]
        indexes = [
            models.Index(fields=["product", "is_active"], name="product_image_active_idx"),
            models.Index(fields=["product", "is_default"], name="product_image_default_idx"),
            models.Index(fields=["sort_order", "created_at"], name="product_image_sort_idx"),
        ]

    def __str__(self):
        product_name = self.product.name if self.product_id else "unassigned product"
        return f"Image for {product_name} (Default: {self.is_default})"

    def clean(self):
        return None

    def save(self, *args, **kwargs):
        if not self.alt_text and self.product_id:
            self.alt_text = self.product.name
        if self.is_default and self.product_id:
            ProductImage.objects.filter(product_id=self.product_id, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)
        if self.image and not str(self.image).startswith("http"):
            upload_result = cloudinary.uploader.upload(
                self.image.file, folder="product_images"
            )
            self.image = upload_result["url"]
        super().save(*args, **kwargs)

    @property
    def image_url(self):
        if self.image:
            return getattr(self.image, "url", str(self.image))
        return ""


class Review(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    rating = models.PositiveIntegerField(
        choices=[(i, f"{i} Stars") for i in range(1, 6)]
    )
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "product_review"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "is_verified"], name="review_product_verified_idx"),
            models.Index(fields=["rating"], name="review_rating_idx"),
            models.Index(fields=["created_at"], name="review_created_idx"),
        ]

    def __str__(self):
        return f"Review by {self.user} for {self.product.name}"
