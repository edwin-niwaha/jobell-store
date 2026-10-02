from django.core.management.base import BaseCommand

from apps.inventory.services import backfill_default_product_variations


class Command(BaseCommand):
    help = "Create default ProductVolume rows for active legacy products without variations."

    def handle(self, *args, **options):
        result = backfill_default_product_variations()
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {result['created']} default variation(s); "
                f"skipped {result['skipped']} product(s)."
            )
        )
