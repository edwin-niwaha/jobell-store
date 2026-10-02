from repositories.product_repository import ProductRepository


class ProductService:
    def __init__(self, repository=None):
        self.repository = repository or ProductRepository()

    def get_categories(self):
        return self.repository.list_categories()

    def get_products(self, *, search="", category=None, featured=None, active=True):
        return self.repository.list_products(
            search=search,
            category=category,
            featured=featured,
            active=active,
        )

    def get_product(self, lookup):
        return self.repository.get_product(lookup)

    def get_product_variants(self, product):
        return self.repository.list_product_variants(product)


product_service = ProductService()
