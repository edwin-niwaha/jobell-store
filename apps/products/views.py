import logging

from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import IntegrityError
from django.db.models import Sum, F, Q, Count, Prefetch
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from apps.inventory.models import Inventory
from apps.products.selectors import (
    active_products_queryset,
    build_storefront_cards,
)

# Import models and forms
from .models import Category, Volume, ProductVolume, Product, ProductImage
from .forms import (
    CategoryForm,
    VolumeForm,
    ProductVolumeForm,
    ProductForm,
    ProductImageForm,
    VolumeSelectionForm,
    ProductFilterForm,
)


# Import custom decorators
from apps.authentication.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
    admin_required,
)

logger = logging.getLogger(__name__)


def _product_identity_filter(cleaned_data):
    """Return only stable product identity fields for duplicate checks."""
    return {
        "name__iexact": cleaned_data.get("name", "").strip(),
        "category": cleaned_data.get("category"),
        "supplier": cleaned_data.get("supplier"),
        "gender": cleaned_data.get("gender"),
    }


def shop_homepage_view(request):
    # Initialize the filter form
    form = ProductFilterForm(request.GET)
    categories = Category.objects.filter(is_active=True, products__status="ACTIVE").distinct().order_by("name")
    selected_category = None

    # Start with all active products
    products = active_products_queryset().order_by("name")

    # Apply filters if the form is valid
    if form.is_valid():
        category_filter = form.cleaned_data.get("category")
        min_price = form.cleaned_data.get("min_price")
        max_price = form.cleaned_data.get("max_price")
        search_query = form.cleaned_data.get("search")

        # Filter by category if selected
        if category_filter:
            products = products.filter(category=category_filter)
            selected_category = category_filter

        # Filter by price range if provided
        if min_price is not None and max_price is not None:
            products = products.filter(
                Q(productvolume__price__gte=min_price)
                | Q(productvolume__price__isnull=True, productvolume__volume__price__gte=min_price),
                Q(productvolume__price__lte=max_price)
                | Q(productvolume__price__isnull=True, productvolume__volume__price__lte=max_price),
            ).distinct()
        elif min_price is not None:
            products = products.filter(
                Q(productvolume__price__gte=min_price)
                | Q(productvolume__price__isnull=True, productvolume__volume__price__gte=min_price)
            ).distinct()
        elif max_price is not None:
            products = products.filter(
                Q(productvolume__price__lte=max_price)
                | Q(productvolume__price__isnull=True, productvolume__volume__price__lte=max_price)
            ).distinct()

        # Filter by search query if provided
        if search_query:
            products = products.filter(name__icontains=search_query)

    # Pagination setup
    paginator = Paginator(products, 32)
    page_number = request.GET.get("page", 1)

    try:
        page_number = int(page_number)
        if page_number < 1:
            page_number = 1
    except ValueError:
        page_number = 1

    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    products_with_images = build_storefront_cards(page_obj)

    # Pass the form, filtered products, and pagination to the template
    return render(
        request,
        "products/shop_products.html",
        {
            "form": form,
            "products_with_images": products_with_images,
            "page_obj": page_obj,
            "categories": categories,
            "selected_category": selected_category,
            "result_count": paginator.count,
        },
    )


@login_required
@admin_or_manager_or_staff_required
def categories_list_view(request):
    search_query = request.GET.get(
        "search", ""
    )  # Get the search query from the request
    categories = Category.objects.annotate(product_count=Count("products")).order_by(
        "name"
    )

    # Filter categories based on the search query
    if search_query:
        categories = categories.filter(name__icontains=search_query)

    # Paginate the filtered categories
    paginator = Paginator(categories, 10)  # Show 10 categories per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "active_icon": "products_categories",
        "categories": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
    }
    return render(request, "products/categories.html", context)


# =================================== categories add view ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def categories_add_view(request):
    context = {
        "active_icon": "products_categories",
    }

    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            # Check if a category with the same name already exists
            category_name = form.cleaned_data["name"]
            if Category.objects.filter(name=category_name).exists():
                messages.error(
                    request,
                    f"A category with the name '{category_name}' already exists.",
                    extra_tags="warning",
                )
            else:
                try:
                    # Save the form data
                    form.save()
                    messages.success(
                        request,
                        f"Category: {category_name} created successfully!",
                        extra_tags="bg-success",
                    )
                    return redirect("products:categories_list")
                except Exception:
                    logger.exception("Error creating category %s", category_name)
                    messages.error(
                        request,
                        "There was an error during the creation!",
                        extra_tags="bg-danger",
                    )
                    return redirect("products:categories_add")
        else:
            messages.error(
                request,
                "Please correct the errors below.",
                extra_tags="warning",
            )
    else:
        form = CategoryForm()

    context["form"] = form
    return render(request, "products/categories_add.html", context=context)


# =================================== categories update view ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def categories_update_view(request, category_id):
    # Get the category or return a 404 error if not found
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            try:
                # Save the form data
                form.save()
                messages.success(
                    request,
                    f"Category: {form.cleaned_data['name']} updated successfully!",
                    extra_tags="bg-success",
                )
                return redirect("products:categories_list")
            except Exception:
                logger.exception("Error updating category %s", category_id)
                messages.error(
                    request,
                    "There was an error during the update!",
                    extra_tags="bg-danger",
                )
                return redirect("products:categories_list")
        else:
            messages.error(
                request,
                "Please correct the errors below.",
                extra_tags="warning",
            )
    else:
        form = CategoryForm(instance=category)

    context = {
        "active_icon": "products_categories",
        "form": form,
        "category": category,
    }

    return render(request, "products/categories_update.html", context=context)


# =================================== categories delete view ===================================
@login_required
@admin_required
@transaction.atomic
def categories_delete_view(request, category_id):
    try:
        # Get the category to delete
        category = Category.objects.get(id=category_id)
        category.delete()
        messages.success(
            request,
            "¡Category: " + category.name + " deleted!",
            extra_tags="bg-success",
        )
        return redirect("products:categories_list")
    except Exception:
        logger.exception("Error deleting category %s", category_id)
        messages.success(
            request,
            "There was an error during the elimination!",
            extra_tags="bg-danger",
        )
        return redirect("products:categories_list")


# # =================================== volumes(ML) List view ===================================
@login_required
@admin_or_manager_or_staff_required
def volume_list(request):
    search_query = request.GET.get(
        "search", ""
    )  # Get the search query from the request
    volumes = Volume.objects.all()

    # Filter categories based on the search query
    if search_query:
        volumes = volumes.filter(ml__icontains=search_query)

    # Paginate the filtered categories
    paginator = Paginator(volumes, 20)  # Show 20 categories per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calculate totals
    total_ml = sum(volume.ml for volume in volumes)
    total_cost = sum(volume.cost for volume in volumes)
    total_price = sum(volume.price for volume in volumes)

    context = {
        "table_title": "Volumes",
        "volumes": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "total_ml": total_ml,
        "total_cost": total_cost,
        "total_price": total_price,
    }
    return render(request, "products/volume_ml_list.html", context)


# # =================================== volumes(ML) add view ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def volume_add_view(request):
    if request.method == "POST":
        form = VolumeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Volume added successfully.", extra_tags="bg-success"
            )
            return redirect("products:volume_add")  # Redirect to a list or detail view
    else:
        form = VolumeForm()

    return render(request, "products/volume_ml.html", {"form": form, "action": "Add"})


# # =================================== volumes(ML) update view ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def volume_update_view(request, volume_id):
    volume = get_object_or_404(Volume, id=volume_id)
    if request.method == "POST":
        form = VolumeForm(request.POST, request.FILES, instance=volume)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Volume updated successfully.", extra_tags="bg-success"
            )
            return redirect("products:volume_list")  # Redirect to a list or detail view
    else:
        form = VolumeForm(instance=volume)

    return render(
        request, "products/volume_ml_update.html", {"form": form, "action": "Update"}
    )


# =================================== volumes(ML) delete ===================================
@login_required
@admin_required
@transaction.atomic
def delete_volume_view(request, volume_id):
    # Get the volume object or return a 404 if not found
    volume = get_object_or_404(Volume, id=volume_id)

    # Delete the volume instance
    volume.delete()
    messages.success(request, "Volume deleted!", extra_tags="bg-danger")

    # Redirect to a page after the deletion (e.g., volume list or product page)
    return redirect(reverse("products:volume_list"))


# =================================== Product volumes view ===================================
@login_required
@admin_or_manager_or_staff_required
def product_volume_list_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Search functionality
    query = request.GET.get("q", "")
    product_volumes = ProductVolume.objects.filter(product=product).order_by(
        "volume__ml"
    )
    if query:
        product_volumes = product_volumes.filter(
            Q(product_type__icontains=query)
            | Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(barcode__icontains=query)
            | Q(color__icontains=query)
            | Q(size__icontains=query)
            | Q(scent__icontains=query)
            | Q(volume__ml__icontains=query)
            | Q(volume__cost__icontains=query)
            | Q(volume__price__icontains=query)
        )

    # Pagination
    paginator = Paginator(product_volumes, 20)  # 20 items per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calculate totals
    total_ml = sum(volume.volume.ml for volume in product_volumes)
    total_cost = sum(volume.volume.cost for volume in product_volumes)
    total_price = sum(volume.volume.price for volume in product_volumes)

    # Calculate totals for discount_value and get_discounted_price
    total_discount_value = sum(volume.discount_value or 0 for volume in product_volumes)
    total_discounted_price = sum(
        volume.get_discounted_price() or 0 for volume in product_volumes
    )

    context = {
        "product": product,
        "product_volumes": page_obj,
        "total_ml": total_ml,
        "total_cost": total_cost,
        "total_price": total_price,
        "total_discount_value": total_discount_value,
        "total_discounted_price": total_discounted_price,
        "query": query,
        "paginator": paginator,
        "page_obj": page_obj,
    }
    return render(request, "products/volumes.html", context)


# =================================== Product volumes add view ===================================


@login_required
@admin_or_manager_or_staff_required
def add_product_volume_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        form = ProductVolumeForm(request.POST, request.FILES)
        form.product = product  # Set the product explicitly before validation

        if form.is_valid():
            volume = form.cleaned_data["volume"]
            product_type = form.cleaned_data["product_type"]

            try:
                with transaction.atomic():
                    form.save()
                    messages.success(
                        request,
                        "Product variation added successfully!",
                        extra_tags="bg-success",
                    )
                    return redirect(
                        "products:product_volume_list", product_id=product.id
                    )
            except IntegrityError:
                form.add_error(None, "This product variation already exists or uses a duplicate SKU/barcode.")
        else:
            # Form is not valid
            messages.error(request, "Please correct the errors below.")

    else:
        form = ProductVolumeForm()
        form.product = product  # Set the product explicitly for the initial form

    return render(
        request, "products/volumes_add.html", {"form": form, "product": product}
    )


# # =================================== Product volumes update view ===================================
@login_required
@admin_or_manager_or_staff_required
def update_product_volume_view(request, product_id, volume_id):
    # Fetch the related product and product volume
    product = get_object_or_404(Product, id=product_id)
    product_volume = get_object_or_404(ProductVolume, id=volume_id, product=product)

    if request.method == "POST":
        form = ProductVolumeForm(
            request.POST, request.FILES, instance=product_volume, product=product
        )
        if form.is_valid():
            form.save()
            # Add success message
            messages.success(
                request, "Product volume updated successfully!", extra_tags="bg-success"
            )
            return redirect("products:product_volume_list", product_id=product.id)
    else:
        form = ProductVolumeForm(instance=product_volume, product=product)

    return render(
        request, "products/volumes_update.html", {"form": form, "product": product}
    )


# ================================ Product delete volume =================================
@login_required
@admin_required
@transaction.atomic
def delete_product_volume_view(request, volume_id):
    product_volume = get_object_or_404(ProductVolume, id=volume_id)
    product_id = product_volume.product.id

    # Delete the product volume
    product_volume.delete()

    # Add success message
    messages.success(request, "Record deleted!", extra_tags="bg-danger")

    # Redirect to the product volume list
    return redirect("products:product_volume_list", product_id=product_id)


@login_required
@admin_or_manager_or_staff_required
def products_list_all(request):
    # Fetch products with prefetch_related for volumes and images
    products = (
        Product.objects.prefetch_related("productvolume_set", "images")
        .all()
        .order_by("name")
    )

    # Calculate totals using inventory quantities
    total_stock = sum(
        product.inventory.quantity for product in products if product.inventory
    )

    total_ml = (
        products.aggregate(total_ml=Sum("productvolume__volume__ml"))["total_ml"] or 0
    )
    total_cost = (
        products.aggregate(total_cost=Sum("productvolume__volume__cost"))["total_cost"]
        or 0
    )
    total_price = (
        products.aggregate(total_price=Sum("productvolume__volume__price"))[
            "total_price"
        ]
        or 0
    )

    context = {
        "products": products,
        "total_stock": total_stock,
        "total_ml": total_ml,
        "total_cost": total_cost,
        "total_price": total_price,
    }

    return render(request, "products/products_list_all.html", context)


# =================================== produts list view ===================================
@login_required
@admin_or_manager_or_staff_required
def products_list_view(request):
    search_query = request.GET.get("search", "")
    page = request.GET.get("page", 1)

    # Filter products based on the search query
    active_variants = ProductVolume.objects.filter(is_active=True).select_related(
        "volume"
    )
    active_images = ProductImage.objects.filter(is_active=True).order_by(
        "-is_default", "sort_order", "-created_at"
    )
    products = (
        Product.objects.select_related("category", "supplier", "inventory")
        .prefetch_related(
            Prefetch(
                "productvolume_set",
                queryset=active_variants,
                to_attr="admin_active_variants",
            ),
            Prefetch("images", queryset=active_images, to_attr="admin_images"),
        )
        .annotate(variant_count=Count("productvolume", distinct=True))
        .filter(
            Q(name__icontains=search_query)
            | Q(category__name__icontains=search_query)
            | Q(supplier__name__icontains=search_query)
        )
        .order_by("name")
    )

    # Pagination
    paginator = Paginator(products, 25)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    # Calculate totals
    total_price = (
        ProductVolume.objects.filter(product__inventory__isnull=False).aggregate(
            total_price=Sum(F("volume__price") * F("product__inventory__quantity"))
        )["total_price"]
        or 0
    )

    total_cost = (
        ProductVolume.objects.filter(product__inventory__isnull=False).aggregate(
            total_cost=Sum(F("volume__cost") * F("product__inventory__quantity"))
        )["total_cost"]
        or 0
    )

    total_stock = (
        Product.objects.aggregate(total_stock=Sum("inventory__quantity"))["total_stock"]
        or 0
    )

    context = {
        "products": products,
        "total_price": total_price,
        "total_cost": total_cost,
        "total_stock": total_stock,
        "table_title": "Products List",
        "search_query": search_query,
    }

    return render(request, "products/products.html", context=context)


# =================================== products add view ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def products_add_view(request):
    is_modal = request.GET.get("modal") == "1" or request.POST.get("modal") == "1"
    context = {
        "product_status": Product.status.field.choices,
        "table_title": "Add Product",
        "is_modal": is_modal,
        "submit_label": "Add product",
    }

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            # Check if a product with the same attributes exists
            attributes = form.cleaned_data
            if Product.objects.filter(**_product_identity_filter(attributes)).exists():
                messages.error(
                    request, "Product already exists!", extra_tags="bg-warning"
                )
                if is_modal:
                    return redirect(f"{reverse('products:products_add')}?modal=1")
                return redirect("products:products_add")

            try:
                form.save()
                messages.success(
                    request,
                    f"Product: {attributes['name']} created successfully!",
                    extra_tags="bg-success",
                )
                return redirect("products:products_list")
            except Exception:
                logger.exception("Error creating product")
                messages.error(
                    request,
                    "There was an error during the creation!",
                    extra_tags="bg-danger",
                )
                if is_modal:
                    return redirect(f"{reverse('products:products_add')}?modal=1")
                return redirect("products:products_add")
        else:
            messages.error(
                request,
                "There were errors in the form submission.",
                extra_tags="bg-danger",
            )
    else:
        form = ProductForm()

    context["form"] = form
    if is_modal:
        return render(request, "products/_product_form_modal.html", context=context)
    return render(request, "products/products_add.html", context=context)


# =================================== products update view ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def products_update_view(request, product_uuid):
    is_modal = request.GET.get("modal") == "1" or request.POST.get("modal") == "1"
    # Get the product or return 404 if not found
    product = get_object_or_404(Product, uuid=product_uuid)

    context = {
        "table_title": "Update Product",
        "product_status": Product.status.field.choices,
        "product": product,
        "categories": Category.objects.all(),
        "is_modal": is_modal,
        "submit_label": "Update product",
    }

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            # Check if a product with the same attributes exists, excluding the current product
            attributes = form.cleaned_data
            if (
                Product.objects.filter(**_product_identity_filter(attributes))
                .exclude(uuid=product_uuid)
                .exists()
            ):
                messages.error(
                    request,
                    "Product with the same attributes already exists!",
                    extra_tags="warning",
                )
                if is_modal:
                    return redirect(
                        f"{reverse('products:products_update', kwargs={'product_uuid': product_uuid})}?modal=1"
                    )
                return redirect("products:products_update", product_uuid=product_uuid)

            try:
                form.save()
                messages.success(
                    request,
                    f"Product: {product.name} updated successfully!",
                    extra_tags="bg-success",
                )
                return redirect("products:products_list")
            except Exception:
                logger.exception("Error updating product %s", product_uuid)
                messages.error(
                    request,
                    "There was an error during the update!",
                    extra_tags="bg-danger",
                )
                if is_modal:
                    return redirect(
                        f"{reverse('products:products_update', kwargs={'product_uuid': product_uuid})}?modal=1"
                    )
                return redirect("products:products_update", product_uuid=product_uuid)
        else:
            messages.error(
                request,
                "There were errors in the form submission.",
                extra_tags="bg-danger",
            )
    else:
        form = ProductForm(instance=product)

    context["form"] = form
    if is_modal:
        return render(request, "products/_product_form_modal.html", context=context)
    return render(request, "products/products_update.html", context=context)


# =================================== products delete view ===================================
@login_required
@admin_required
@transaction.atomic
def products_delete_view(request, product_uuid):
    try:
        # Get the product to delete
        product = Product.objects.get(uuid=product_uuid)
        product.delete()
        messages.success(
            request, "¡Product: " + product.name + " deleted!", extra_tags="bg-success"
        )
        return redirect("products:products_list")
    except Exception:
        logger.exception("Error deleting product %s", product_uuid)
        messages.success(
            request,
            "There was an error during the elimination!",
            extra_tags="bg-danger",
        )
        return redirect("products:products_list")


# =================================== Stock alerts view ===================================
@login_required
@admin_or_manager_or_staff_required
def stock_alerts_view(request):
    # Fetch all products with inventory details
    low_stock_products = Inventory.objects.filter(
        quantity__lte=F("low_stock_threshold"),
        quantity__gt=0,  # Low stock but not 0
    ).select_related(
        "product"
    )  # Ensures related product data is fetched

    out_of_stock_products = Inventory.objects.filter(
        quantity=0  # Out of stock
    ).select_related("product")

    context = {
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock_products,
    }

    return render(request, "products/stock_alerts.html", context)


# =================================== Upload Product Image ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def update_product_image(request):
    if request.method == "POST":
        product_id = request.POST.get("id")
        product = get_object_or_404(Product, id=product_id)
        form = ProductImageForm(
            request.POST,
            request.FILES,
            instance=ProductImage(product=product),
        )
        if form.is_valid():
            new_picture = form.save(commit=False)
            new_picture.product = product
            new_picture.save()

            if new_picture.is_default:
                product.hero_image = new_picture.image
                product.save(update_fields=["hero_image"])

            messages.success(
                request, "Product image updated successfully!", extra_tags="bg-success"
            )
            return redirect("products:update_product_image")
        else:
            messages.error(request, "Form is invalid.", extra_tags="bg-danger")
    else:
        form = ProductImageForm()

    # Fetch all products
    products = Product.objects.all().order_by("id")

    return render(
        request,
        "products/product_image_add.html",
        {
            "form": form,
            "form_name": "Upload Product Image",
            "products": products,
            "table_title": "Upload Image",
        },
    )


# =================================== View Product Image ===================================
@login_required
@admin_or_manager_or_staff_required
def product_images(request):
    products = Product.objects.order_by("name")
    product_id = request.POST.get("id") if request.method == "POST" else request.GET.get("id")
    selected_product = None
    images = ProductImage.objects.none()
    if product_id:
        selected_product = get_object_or_404(Product, id=product_id)
        images = ProductImage.objects.select_related("product").filter(
            product=selected_product
        ).order_by("-is_default", "sort_order", "-created_at")
        if not images.exists():
            messages.error(
                request,
                "No images found for the selected product.",
                extra_tags="bg-warning",
            )

    paginator = Paginator(images, 24)
    page_number = request.GET.get("page")
    product_images_page = paginator.get_page(page_number)

    context = {
        "table_title": "Product Images",
        "products": products,
        "selected_product": selected_product,
        "selected_product_id": str(product_id or ""),
        "product_image_fetched": product_images_page,
        "has_selected_product": bool(selected_product),
        "total_images": images.count(),
        "default_images": images.filter(is_default=True).count(),
        "active_images": images.filter(is_active=True).count(),
    }
    return render(request, "products/product_images.html", context)


# =================================== Delete Product Image ===================================
@login_required
@admin_required
@transaction.atomic
def delete_product_image(request, pk):
    records = ProductImage.objects.get(id=pk)
    records.delete()
    messages.info(request, "Record deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("products:product_images"))


# =================================== Discounted Poducts ===================================
def discounted_product_list_view(request):
    # Fetch products with at least one discounted volume
    discounted_products = (
        Product.objects.filter(
            productvolume__discount_value__gt=0  # Filtering products that have at least one volume with discount
        )
        .distinct()
        .order_by("name")
    )

    # Paginate the discounted products (12 items per page)
    paginator = Paginator(
        discounted_products, 12
    )  # Show 12 discounted products per page
    page_number = request.GET.get(
        "page"
    )  # Get the current page number from the request
    page_obj = paginator.get_page(page_number)  # Get the page object

    # Fetch the default image and discounted prices for each discounted product
    for product in page_obj:
        product.default_image = ProductImage.objects.filter(
            product=product, is_default=True
        ).first()
        # Add discounted volumes to the product
        # product.discounted_volumes = ProductVolume.objects.filter(
        #     product=product, discount_value__gt=0
        # )
        product.discounted_volumes = ProductVolume.objects.filter(
            product=product, discount_value__gt=0
        ).order_by("volume__ml")

    # Pass the page object to the template
    context = {
        "page_obj": page_obj,
    }
    return render(request, "products/discounted_products.html", context)


# =================================== add_volume_to_all Poducts ===================================


@login_required
@admin_required
def add_volume_to_all_products_view(request):
    """Handle form submission and add a selected volume with a product type to all products."""
    if request.method == "POST":
        form = VolumeSelectionForm(request.POST)
        if form.is_valid():
            volume = form.cleaned_data["volume"]
            product_type = form.cleaned_data["product_type"]
            products = Product.objects.all()

            product_volumes = []
            existing_combinations = 0  # Counter for existing combinations

            # Check for existing combinations to avoid duplicates
            for product in products:
                # Check if the combination of product, volume, and product type already exists
                if not ProductVolume.objects.filter(
                    product=product, volume=volume, product_type=product_type, color="", size="", scent=""
                ).exists():
                    product_volumes.append(
                        ProductVolume(
                            product=product,
                            volume=volume,
                            product_type=product_type,
                        )
                    )
                else:
                    existing_combinations += (
                        1  # Increment the counter if combination already exists
                    )

            # Bulk insert while avoiding duplicates
            ProductVolume.objects.bulk_create(product_volumes, ignore_conflicts=True)

            # Messages based on whether new records were added or not
            if product_volumes:
                messages.success(
                    request,
                    f"Successfully Added {len(product_volumes)} ProductVolume records for {volume.ml}ML ({product_type})",
                    extra_tags="bg-success",
                )
            if existing_combinations > 0:
                messages.info(
                    request,
                    f"Oops! {existing_combinations} ProductVolume combinations already existed and were not added.",
                    extra_tags="bg-danger",
                )

            return redirect(
                "products:add-volume-to-all-products"
            )  # Redirect to prevent resubmission issues

    else:
        form = VolumeSelectionForm()

    return render(
        request,
        "products/add_volume_all.html",
        {
            "form": form,
            "form_title": "Add Volume to All Products",
        },
    )


# =================================== delete_selected_volumes_view ===================================
@login_required
@admin_required
def delete_selected_volumes_view(request):
    """Delete all ProductVolume records for a selected volume and product type."""
    if request.method == "POST":
        form = VolumeSelectionForm(request.POST)
        if form.is_valid():
            volume = form.cleaned_data["volume"]
            product_type = form.cleaned_data["product_type"]

            # Delete records that match the selected volume and product type
            deleted_count, _ = ProductVolume.objects.filter(
                volume=volume, product_type=product_type
            ).delete()

            if deleted_count > 0:
                messages.success(
                    request,
                    f"Successfully deleted {deleted_count} ProductVolume records for {volume.ml}ML ({product_type}).",
                    extra_tags="bg-success",
                )
            else:
                messages.info(
                    request,
                    f"No records found for {volume.ml}ML ({product_type}) to delete.",
                    extra_tags="bg-warning",
                )

            return redirect(
                "products:delete-selected-volumes"
            )  # Redirect after deletion

    else:
        form = VolumeSelectionForm()

    return render(
        request,
        "products/delete_selected_volumes.html",
        {
            "form": form,
            "form_title": "Delete Selected Volume Records",
        },
    )


# =================================== All product_volumes_list_view ===================================


@login_required
@admin_or_manager_required
def product_volumes_list_view(request):
    """Display all volumes for products."""

    # Retrieve search query
    search_query = request.GET.get("search", "")

    # Query to get all volumes, optionally filter or order as needed
    if search_query:
        # Search by product name or volume size (ML)
        volumes = ProductVolume.objects.filter(
            Q(volume__ml__icontains=search_query)
            | Q(product__name__icontains=search_query)
            | Q(name__icontains=search_query)
            | Q(sku__icontains=search_query)
            | Q(barcode__icontains=search_query)
            | Q(color__icontains=search_query)
            | Q(size__icontains=search_query)
            | Q(scent__icontains=search_query)
        ).select_related("product", "volume")
    else:
        volumes = (
            ProductVolume.objects.all()
            .select_related("product", "volume")
            .order_by("product__name", "product_type")
        )

    # Calculate totals (if necessary)
    total_ml = sum(volume.volume.ml for volume in volumes)
    total_cost = sum(volume.volume.cost for volume in volumes)
    total_price = sum(volume.volume.price for volume in volumes)

    # Calculate totals for discount_value and get_discounted_price
    total_discount_value = sum(volume.discount_value or 0 for volume in volumes)
    total_discounted_price = sum(
        volume.get_discounted_price() or 0 for volume in volumes
    )
    # Pagination (if applicable)
    paginator = Paginator(volumes, 100)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "products/product_volumes_list.html",
        {
            "volumes": page_obj,
            "total_ml": total_ml,
            "total_cost": total_cost,
            "total_price": total_price,
            "total_discount_value": total_discount_value,
            "total_discounted_price": total_discounted_price,
            "search_query": search_query,  # Pass the search query
            "table_title": "All Product Volumes",
        },
    )
