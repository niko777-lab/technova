from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import CheckoutForm
from .models import Brand, Category, Order, OrderItem, Product

SORT_OPTIONS = {
    "newest": ("Newest first", "-created_at"),
    "price_asc": ("Price: low to high", "price"),
    "price_desc": ("Price: high to low", "-price"),
    "name": ("Name: A to Z", "name"),
}


class OutOfStock(Exception):
    pass


def _to_decimal(value):
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError):
        return None
    return number if number.is_finite() else None


def home(request):
    base = Product.objects.select_related("category", "brand")
    context = {
        "categories": Category.objects.all(),
        "sale_products": base.filter(old_price__gt=F("price"), stock__gt=0)[:4],
        "new_products": base[:8],
    }
    return render(request, "store/home.html", context)


def product_list(request, category_slug=None):
    products = Product.objects.select_related("category", "brand")
    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(brand__name__icontains=query)
        )

    brand_slug = request.GET.get("brand", "")
    if brand_slug:
        products = products.filter(brand__slug=brand_slug)

    min_price = _to_decimal(request.GET.get("min_price"))
    max_price = _to_decimal(request.GET.get("max_price"))
    if min_price is not None:
        products = products.filter(price__gte=min_price)
    if max_price is not None:
        products = products.filter(price__lte=max_price)

    if request.GET.get("sale"):
        products = products.filter(old_price__gt=F("price"))

    if request.GET.get("in_stock"):
        products = products.filter(stock__gt=0)

    sort = request.GET.get("sort", "newest")
    if sort not in SORT_OPTIONS:
        sort = "newest"
    products = products.order_by(SORT_OPTIONS[sort][1], "-id")

    brands = Brand.objects.all()
    if category:
        brands = brands.filter(products__category=category).distinct()

    page_obj = Paginator(products, 9).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "category": category,
        "page_obj": page_obj,
        "brands": brands,
        "query": query,
        "sort": sort,
        "sort_options": [(key, label) for key, (label, _) in SORT_OPTIONS.items()],
        "querystring": params.urlencode(),
    }
    return render(request, "store/product_list.html", context)


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category", "brand"), slug=slug)
    related = (
        Product.objects.select_related("category", "brand")
        .filter(category=product.category)
        .exclude(pk=product.pk)[:4]
    )
    return render(request, "store/product_detail.html", {"product": product, "related": related})


# ---------- cart ----------

def cart_detail(request):
    items = list(Cart(request))
    total = sum(item["line_total"] for item in items)
    return render(request, "store/cart.html", {"items": items, "total": total})


def _safe_next(request, default="cart"):
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return target
    return default


def _quantity(request, default=1):
    try:
        return int(request.POST.get("quantity", default))
    except (TypeError, ValueError):
        return default


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if not product.in_stock:
        messages.error(request, f"{product.name} is out of stock.")
        return redirect(_safe_next(request))
    cart = Cart(request)
    cart.add(product, max(_quantity(request), 1))
    messages.success(request, f"{product.name} was added to your cart.")
    return redirect(_safe_next(request))


@require_POST
def cart_update(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    Cart(request).set(product, _quantity(request, 0))
    return redirect("cart")


@require_POST
def cart_remove(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    Cart(request).remove(product)
    messages.success(request, f"{product.name} was removed from your cart.")
    return redirect("cart")


# ---------- checkout & orders ----------

def checkout(request):
    cart = Cart(request)
    items = list(cart)
    if not items:
        messages.error(request, "Your cart is empty.")
        return redirect("cart")
    total = sum(item["line_total"] for item in items)

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    order = form.save(commit=False)
                    if request.user.is_authenticated:
                        order.user = request.user
                    order.save()
                    for item in items:
                        product = Product.objects.select_for_update().get(pk=item["product"].pk)
                        if product.stock < item["quantity"]:
                            raise OutOfStock(product.name)
                        product.stock -= item["quantity"]
                        product.save(update_fields=["stock"])
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            name=product.name,
                            price=product.price,
                            quantity=item["quantity"],
                        )
            except OutOfStock as error:
                messages.error(request, f"Not enough stock for {error}. Update your cart and try again.")
                return redirect("cart")
            cart.clear()
            request.session["last_order"] = order.pk
            return redirect("order_success")
    else:
        initial = {}
        if request.user.is_authenticated:
            initial["full_name"] = request.user.get_full_name()
        form = CheckoutForm(initial=initial)

    return render(request, "store/checkout.html", {"form": form, "items": items, "total": total})


def order_success(request):
    order_id = request.session.get("last_order")
    if not order_id:
        return redirect("home")
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=order_id)
    return render(request, "store/order_success.html", {"order": order})


@login_required
def profile(request):
    orders = request.user.orders.prefetch_related("items")
    return render(request, "store/profile.html", {"orders": orders})


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your account is ready.")
        return redirect("home")
    return render(request, "registration/register.html", {"form": form})
