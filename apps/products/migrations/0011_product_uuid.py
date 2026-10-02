# products/migrations/0011_add_product_uuid.py

from django.db import migrations, models
import uuid


# A more streamlined function to generate UUIDs
def generate_uuids(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    # We select only the products that need a UUID
    products_to_update = Product.objects.filter(uuid__isnull=True)

    for product in products_to_update:
        product.uuid = uuid.uuid4()

    # Use a single bulk_update call. Django handles the batching.
    if products_to_update:
        Product.objects.bulk_update(products_to_update, ["uuid"], batch_size=1000)


def reverse_generate_uuids(apps, schema_editor):
    # This reverse function is perfect as is
    Product = apps.get_model("products", "Product")
    Product.objects.update(uuid=None)


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0010_remove_productimage_updated_at"),
    ]

    operations = [
        # Step 1: Add the uuid field as nullable, without a default.
        migrations.AddField(
            model_name="Product",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        # Step 2: Populate the uuid for all existing records.
        migrations.RunPython(generate_uuids, reverse_code=reverse_generate_uuids),
        # Step 3: Alter the field to its final state: non-nullable and unique.
        migrations.AlterField(
            model_name="Product",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
    ]


# This migration adds a UUID field to the Product model, populates it for existing records,
# and then alters the field to be non-nullable and unique. The reverse function clears the UUIDs.
