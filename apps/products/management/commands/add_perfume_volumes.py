from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.products.models import Product, ProductVolume, Volume

OPTIONS = (
    ('Roll-On', 3, 5000), ('Roll-On', 6, 10000),
    ('Spray', 9, 10000), ('Spray', 10, 15000),
    ('Roll-On', 12, 20000), ('Spray', 12, 20000),
    ('Spray', 15, 25000), ('Spray', 18, 25000),
    ('Spray', 20, 30000), ('Spray', 24, 35000),
    ('Spray', 30, 45000), ('Spray', 50, 80000), ('Spray', 100, 150000),
)

class Command(BaseCommand):
    help = 'Add missing standard perfume options without changing existing variants.'

    def add_arguments(self, parser):
        parser.add_argument('--product-id', type=int, action='append')
        parser.add_argument('--dry-run', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        products = Product.objects.exclude(category__name__in=['Mini', 'Car scent'])
        if options['product_id']:
            products = products.filter(pk__in=options['product_id'])
        products = list(products.select_for_update(of=('self',)).order_by('pk'))
        volumes = {v.ml: v for v in Volume.objects.all()}
        missing = {ml for _, ml, _ in OPTIONS} - volumes.keys()
        if missing:
            raise CommandError(f'Configure volume prices and costs first: {sorted(missing)}ML')
        combinations = {}
        for product_id, product_type, ml in ProductVolume.objects.filter(product__in=products).values_list('product_id', 'product_type', 'volume__ml'):
            combinations.setdefault(product_id, set()).add((product_type, ml))
        created = 0
        for product in products:
            existing = combinations.get(product.pk, set())
            for product_type, ml, price in OPTIONS:
                if (product_type, ml) in existing:
                    continue
                self.stdout.write(f'{product.name}: {product_type} - {ml}ML - UGX {price:,}')
                if not options['dry_run']:
                    ProductVolume.objects.create(product=product, product_type=product_type,
                                                 volume=volumes[ml], price=price)
                created += 1
        verb = 'Would add' if options['dry_run'] else 'Added'
        self.stdout.write(self.style.SUCCESS(f'{verb} {created} variant(s) across {len(products)} product(s).'))


