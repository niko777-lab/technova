from .models import Product


class Cart:
    """Session-based shopping cart: {product_id: quantity}."""

    SESSION_KEY = "cart"

    def __init__(self, request):
        self.session = request.session
        self.data = dict(self.session.get(self.SESSION_KEY, {}))

    def _save(self):
        self.session[self.SESSION_KEY] = self.data

    def add(self, product, quantity=1):
        key = str(product.id)
        self.set(product, self.data.get(key, 0) + quantity)

    def set(self, product, quantity):
        key = str(product.id)
        quantity = min(quantity, product.stock)
        if quantity <= 0:
            self.data.pop(key, None)
        else:
            self.data[key] = quantity
        self._save()

    def remove(self, product):
        self.data.pop(str(product.id), None)
        self._save()

    def clear(self):
        self.data = {}
        self._save()

    def __iter__(self):
        products = Product.objects.filter(id__in=self.data.keys()).select_related("category", "brand")
        for product in products:
            quantity = self.data[str(product.id)]
            yield {
                "product": product,
                "quantity": quantity,
                "line_total": product.price * quantity,
            }

    def __len__(self):
        return sum(self.data.values())
