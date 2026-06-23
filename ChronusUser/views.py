from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import APIView, api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
import stripe
from ChronasAdmin.models import Coupon, Notification, Product, Order, OrderItem, SubCategory
from ChronusUser.utils import apply_coupon_to_order
from .models import GuestSession, Cart, CartItem, Wishlist, Review
from ChronasAdmin.models import Category, Brand, Product, Order, Coupon, SubCategory
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Count
from ChronasAdmin.models import ProductColor
from ChronasAdmin.models import FineArtSize, Frame, Material
from .models import Address
# ===============================
# GUEST SESSION
# ===============================
@api_view(["POST"])
@permission_classes([AllowAny])
def create_guest(request):
    guest = GuestSession.objects.create()
    return Response({"guest_id": str(guest.guest_id)})


def get_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)

    else:
        guest_id = (
            request.headers.get("x-guest-id")
            or request.META.get("HTTP_X_GUEST_ID")
        )

        if not guest_id:
            raise Exception("guest_id header required for guest user")

        cart = Cart.objects.filter(guest_id=guest_id).order_by("-id").first()

        if not cart:
            cart = Cart.objects.create(guest_id=guest_id)

    return cart

# ===============================
# CART
# ===============================
@api_view(["POST"])
@permission_classes([AllowAny])
def add_to_cart(request):
    product_id = request.data.get("product_id")
    size_id = request.data.get("size_id")
    frame_id = request.data.get("frame_id")
    material_id = request.data.get("material_id")

    try:
        qty = int(request.data.get("quantity", 1))
    except (TypeError, ValueError):
        return Response({"error": "Invalid quantity"}, status=400)

    if not product_id:
        return Response({"error": "product_id required"}, status=400)

    if qty <= 0:
        return Response({"error": "Invalid quantity"}, status=400)

    cart = get_cart(request)
    product = get_object_or_404(Product, id=product_id)

    size = None
    frame = None
    material = None

    price = product.price

    # product-specific size
    if size_id:
        size = get_object_or_404(FineArtSize, id=size_id, product=product)
        price = size.price

    # only allow frames linked to this product
    if frame_id:
        frame = get_object_or_404(Frame, id=frame_id, products=product)
        price += frame.extra_price

    # only allow materials linked to this product
    if material_id:
        material = get_object_or_404(Material, id=material_id, products=product)
        price += material.extra_price

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        size=size,
        frame=frame,
        material=material,
        defaults={
            "quantity": qty,
            "price": price
        }
    )

    if not created:
        item.quantity += qty
        item.price = price
        item.save()

    return Response({"message": "Added to cart"})

from ChronusUser.currency import convert_price
@api_view(["GET"])
@permission_classes([AllowAny])
def view_cart(request):
    currency = request.GET.get(
        "currency",
        "USD"
    ).upper()
    cart = get_cart(request)

    items = CartItem.objects.select_related(
        "product", "size", "frame", "material"
    ).filter(cart=cart)

    subtotal = 0
    data = []

    for item in items:
        converted_price = convert_price(
            item.price,
            currency
        )
        total = converted_price * item.quantity
        subtotal += total

        data.append({
            "id": item.id,
            "product_id": item.product.id,
            "product": item.product.name,
            # "price": item.price,
            "price": round(
                converted_price,
                2
            ),
            "currency": currency,
            "size": item.size.size if item.size else None,
            "frame": item.frame.name if item.frame else None,
            "material": item.material.name if item.material else None,
            "image": item.product.image.url if item.product.image else None,
            "quantity": item.quantity,
            "total": total
        })

    return Response({
        "currency": currency,
        "items": data,
        "subtotal": round(
            subtotal,
            2
        )
    })


@api_view(["DELETE"])
@permission_classes([AllowAny])
def remove_from_cart(request, product_id):
    cart = get_cart(request)

    try:
        item = CartItem.objects.get(id=product_id, cart=cart)
        item.delete()
        return Response({"message": "Item removed"})
    except CartItem.DoesNotExist:
        return Response({"error": "Item not found"}, status=404)

# ===============================
# WISHLIST
# ===============================
import uuid

@api_view(["POST"])
@permission_classes([AllowAny])
def add_to_wishlist(request):
    product_id = request.data.get("product_id")
    if not product_id:
        return Response({"error": "product_id required"}, status=400)

    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        Wishlist.objects.get_or_create(user=request.user, product=product)
    else:
        guest_id = request.headers.get("guest_id")

        # auto create guest id if missing
        if not guest_id:
            guest_id = str(uuid.uuid4())

        Wishlist.objects.get_or_create(guest_id=guest_id, product=product)

        return Response({
            "message": "Added to wishlist",
            "guest_id": guest_id   # send back so frontend stores it
        })

    return Response({"message": "Added to wishlist"})

# ===============================
# REVIEW
# ===============================
@api_view(["POST"])
@permission_classes([AllowAny])
def add_review(request):
    product_id = request.data.get("product_id")
    rating = request.data.get("rating")
    comment = request.data.get("comment")

    if not product_id or not rating or not comment:
        return Response({"error": "product_id, rating, comment required"}, status=400)

    rating = int(rating)
    if rating < 1 or rating > 5:
        return Response({"error": "Rating must be between 1 and 5"}, status=400)

    Review.objects.create(
        product_id=product_id,
        user=request.user if request.user.is_authenticated else None,
        name=request.data.get("name", "Guest"),
        rating=rating,
        comment=comment
    )

    return Response({"message": "Review added"})


# @api_view(["POST"])
# @permission_classes([AllowAny])
# def checkout(request):
    currency = request.data.get(
            "currency",
            "USD"
        ).upper()
    cart = get_cart(request)

    items = CartItem.objects.select_related(
        "product", "size", "frame", "material"
    ).filter(cart=cart)

    if not items.exists():
        return Response({"error": "Cart is empty"}, status=400)

    total = 0
    for i in items:
        total += i.quantity * i.price

    guest_id = None
    if not request.user.is_authenticated:
        guest_id = request.headers.get("X-Guest-Id")
        if not guest_id:
            return Response({"error": "guest_id required"}, status=400)

    city = request.data.get("city", "")
    postal_code = request.data.get("postal_code", "")
    country = request.data.get("country", "")
    first_name = request.data.get("first_name", "")
    last_name = request.data.get("last_name", "")

    shipping_address = f"{first_name} {last_name}, {city}, {postal_code}, {country}".strip(", ").strip()

    if not shipping_address:
        return Response({"error": "shipping address required"}, status=400)

    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        guest_id=guest_id,
        email=request.data.get("email"),
        phone=request.data.get("phone"),
        shipping_address=shipping_address,
        total_amount=total,
        currency=currency
    )
    Notification.objects.create(
        title="New Order Received",
        message=f"Order #{order.id} has been placed for {order.total_amount}"
    )
    order_items = [
        OrderItem(
            order=order,
            product=i.product,
            size=i.size,
            frame=i.frame,
            material=i.material,
            quantity=i.quantity,
            price=i.price
        )
        for i in items
    ]
    OrderItem.objects.bulk_create(order_items)

    return Response({"order_id": order.id, "amount": total,  "currency": currency})

@api_view(["POST"])
@permission_classes([AllowAny])
def checkout(request):

    currency = request.data.get(
        "currency",
        "USD"
    ).upper()

    cart = get_cart(request)

    items = CartItem.objects.select_related(
        "product",
        "size",
        "frame",
        "material"
    ).filter(
        cart=cart
    )

    if not items.exists():
        return Response(
            {"error": "Cart is empty"},
            status=400
        )

    total = 0

    for item in items:
        total += item.quantity * item.price

    guest_id = None

    if not request.user.is_authenticated:

        guest_id = request.headers.get(
            "X-Guest-Id"
        )

        if not guest_id:
            return Response(
                {"error": "guest_id required"},
                status=400
            )

    address_id = request.data.get(
        "address_id"
    )

    # Logged-in user using saved address
    if request.user.is_authenticated and address_id:

        address = Address.objects.filter(
            id=address_id,
            user=request.user
        ).first()

        if not address:
            return Response(
                {"error": "Address not found"},
                status=404
            )

        shipping_address = (
            f"{address.full_name}, "
            f"{address.address_line_1}, "
            f"{address.city}, "
            f"{address.state}, "
            f"{address.country}, "
            f"{address.postal_code}"
        )

        phone = address.phone

    # Guest checkout OR logged-in user manual address
    else:

        city = request.data.get(
            "city",
            ""
        )

        postal_code = request.data.get(
            "postal_code",
            ""
        )

        country = request.data.get(
            "country",
            ""
        )

        first_name = request.data.get(
            "first_name",
            ""
        )

        last_name = request.data.get(
            "last_name",
            ""
        )

        phone = request.data.get(
            "phone",
            ""
        )

        shipping_address = (
            f"{first_name} {last_name}, "
            f"{city}, "
            f"{postal_code}, "
            f"{country}"
        ).strip(", ").strip()

        if not shipping_address:
            return Response(
                {"error": "shipping address required"},
                status=400
            )

    order = Order.objects.create(
        user=(
            request.user
            if request.user.is_authenticated
            else None
        ),
        guest_id=guest_id,
        email=request.data.get("email"),
        phone=phone,
        shipping_address=shipping_address,
        total_amount=total,
        currency=currency
    )

    Notification.objects.create(
        title="New Order Received",
        message=(
            f"Order #{order.id} "
            f"has been placed for "
            f"{order.total_amount}"
        )
    )

    order_items = [

        OrderItem(
            order=order,
            product=item.product,
            size=item.size,
            frame=item.frame,
            material=item.material,
            quantity=item.quantity,
            price=item.price
        )

        for item in items
    ]

    OrderItem.objects.bulk_create(
        order_items
    )

    return Response({
        "order_id": order.id,
        "amount": total,
        "currency": currency
    })


# ===============================
# USER ORDERS (AUTH)
# ===============================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_orders(request):

    orders = Order.objects.prefetch_related("items__product").filter(user=request.user)

    data = []

    for order in orders:

        items = []
        for item in order.items.all():
            items.append({
                "product_name": item.product.name,
                "quantity": item.quantity,
                "product_image": (
                    item.product.image.url
                    if item.product.image else None
                ),
                "price": convert_price(
                    item.price,
                    order.currency
                ),
                "currency": order.currency
            })

        data.append({
            "id": order.id,
            "status": order.status,
           
            "total_amount": convert_price(
                order.total_amount,
                order.currency
            ),
            "currency": order.currency,
            "created_at": order.created_at,

            "tracking_link": order.tracking_link,
            "tracking_number": order.tracking_number,
            "carrier": order.carrier,
            "shipment_id": order.shipment_id,
            "shipped_at": order.shipped_at,

            "items": items
        })

    return Response({"orders": data})




from .currency import convert_amount
class CreatePaymentIntentView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            order_id = request.data.get(id=order_id)
            if not order_id:
                return Response(
                    {"error":"order_id required"},
                    status=400
                )
            order = Order.objects.get(id=order_id)
            
            # currency = request.data.get("currency", "usd").lower()
            currency = order.currency.lower()
        

            # ✅ SECURITY CHECK

            if request.user.is_authenticated:
                if order.user != request.user:
                    return Response({"error": "Unauthorized order access"}, status=403)

            else:
                guest_id = request.headers.get("X-Guest-Id")

                if not guest_id or order.guest_id != guest_id:
                    return Response({"error": "Unauthorized guest order"}, status=403)

            # Convert order amount based on selected currency
            amount_in_cents = convert_amount(order.total_amount, currency)

            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=currency,
                automatic_payment_methods={"enabled": True},
                
                metadata={
                    "order_id": order.id,
                    "currency": currency,
                    "user_id": request.user.id if request.user.is_authenticated else "",
                    "guest_id": order.guest_id or "",
                }
            )

            return Response({
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id,
                "currency": currency
            })

        except Order.DoesNotExist:
            return Response({"error": "Invalid order"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
# ===============================
# AUTH (JWT)
# ===============================
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    full_name = request.data.get("full_name")
    email = request.data.get("email")
    password = request.data.get("password")

    if not full_name or not email or not password:
        return Response({"error": "full_name, email, password required"}, status=400)

    if User.objects.filter(username=email).exists():
        return Response({"error": "Email already registered"}, status=400)

    parts = full_name.strip().split(" ")
    first_name = parts[0]
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name
    )

    tokens = get_tokens_for_user(user)

    return Response({
        "message": "User created",
        "user_id": user.id,
        "email": user.email,
        "full_name": full_name,
        "tokens": tokens
    }, status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get("email")
    password = request.data.get("password")

    user = authenticate(username=email, password=password)

    if user is None:
        return Response({"error": "Invalid credentials"}, status=401)

    tokens = get_tokens_for_user(user)
    full_name = f"{user.first_name} {user.last_name}".strip()

    return Response({
        "message": "Login successful",
        "user_id": user.id,
        "email": user.email,
        "full_name": full_name,
        "tokens": tokens
    })

from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ChronusUser.currency import convert_price
@csrf_exempt
@require_http_methods(["GET"])
def view_products(request):
    category = request.GET.get("category")
    subcategory = request.GET.get("subcategory")
    search = request.GET.get("search")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    currency = request.GET.get("currency", "USD").upper()   #newwww

    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 12))
    except ValueError:
        return JsonResponse({"error": "Invalid pagination values"}, status=400)

    if page < 1 or limit < 1:
        return JsonResponse({"error": "Page and limit must be greater than 0"}, status=400)

    offset = (page - 1) * limit

    products = Product.objects.filter(is_published=True).select_related(
        "category", "subcategory", "brand"
    ).prefetch_related(
        "sizes",
        "colors",
        "gallery",
        "frames",
        "materials"
    )

    # CATEGORY FILTER
    if category:
        if category.isdigit():
            products = products.filter(category__id=category)
        else:
            products = products.filter(category__name__icontains=category)

    # SUBCATEGORY FILTER
    if subcategory:
        if subcategory.isdigit():
            products = products.filter(subcategory__id=subcategory)
        else:
            products = products.filter(subcategory__name__icontains=subcategory)

    # SEARCH
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(brand__name__icontains=search) |
            Q(category__name__icontains=search) |
            Q(subcategory__name__icontains=search)
        )

    # PRICE FILTER
    if min_price:
        products = products.filter(price__gte=min_price)

    if max_price:
        products = products.filter(price__lte=max_price)

    total_products = products.count()
    total_pages = (total_products + limit - 1) // limit

    products = products[offset:offset + limit]

    data = []

    for product in products:
        data.append({
            "id": product.id,
            "name": product.name,

            "category": {
                "id": product.category.id,
                "name": product.category.name
            } if product.category else None,

            "subcategory": {
                "id": product.subcategory.id,
                "name": product.subcategory.name
            } if product.subcategory else None,

            "brand": {
                "id": product.brand.id,
                "name": product.brand.name
            } if product.brand else None,

            # "price": str(product.price),
            "price": convert_price(
                product.price,
                currency
            ),
            "currency": currency,
            "description": product.description,
            "stock": product.stock,
            "image": product.image.url if product.image else None,
            "created_at": product.created_at,
            "is_featured": product.is_featured,
            "is_best_seller": product.is_best_seller,
            "specification": product.specification,

            "sizes": [
                {
                    "size": s.size,
                    # "price": str(s.price)
                    "price": convert_price(
                        s.price,
                        currency
                    )
                }
                for s in product.sizes.all()
            ],

            "colors": [
                {
                    "id": c.id,
                    "color_name": c.color_name,
                    "image": c.image.url if c.image else None
                }
                for c in product.colors.all()
            ],

            "gallery": [
                img.image.url
                for img in product.gallery.all()
                if img.image
            ],

            "frames": [
                {
                    "id": f.id,
                    "name": f.name,
                    "extra_price": convert_price(
                    f.extra_price,
                    currency
                ) if f.extra_price is not None else None,
                    "image": f.image.url if getattr(f, "image", None) else None
                }
                for f in product.frames.all()
            ],

            "materials": [
                {
                    "id": m.id,
                    "name": m.name,
                    "description": m.description,
                    "extra_price": convert_price(
                        m.extra_price,
                        currency
                    ) if m.extra_price is not None else None
                }
                for m in product.materials.all()
            ]
        })

    return JsonResponse({
        "page": page,
        "limit": limit,
        "total_products": total_products,
        "total_pages": total_pages,
        "products": data
    }, status=200)

from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ChronusUser.currency import convert_price
@csrf_exempt
@require_http_methods(["GET"])
def view_single_product(request, product_id):
    try:
        currency = request.GET.get(
            "currency",
            "USD"
        ).upper()
        product = Product.objects.select_related(
            "category", "subcategory", "brand"
        ).prefetch_related(
            "gallery",
            "sizes",
            "colors",
            "frames",
            "materials"
        ).get(id=product_id,
              is_published=True)

        reviews_qs = Review.objects.filter(product=product).order_by("-created_at")

        rating_summary = reviews_qs.aggregate(
            avg_rating=Avg("rating"),
            total_reviews=Count("id")
        )

        data = {
            "id": product.id,
            "name": product.name,

            "category": {
                "id": product.category.id,
                "name": product.category.name
            } if product.category else None,

            "subcategory": {
                "id": product.subcategory.id,
                "name": product.subcategory.name
            } if product.subcategory else None,

            "brand": {
                "id": product.brand.id,
                "name": product.brand.name
            } if product.brand else None,

            # "price": str(product.price),
            "price": convert_price(
                product.price,
                currency
            ),
            "currency": currency,
            "description": product.description,
            "stock": product.stock,
            "image": product.image.url if product.image else None,

            "gallery": [
                img.image.url
                for img in product.gallery.all()
                if img.image
            ],

            "is_featured": product.is_featured,
            "is_best_seller": product.is_best_seller,
            "created_at": product.created_at,
            "specification": product.specification,

            "sizes": [
                {
                    "id": s.id,
                    "size": s.size,
                    "price": convert_price(
                    s.price,
                    currency
                )
                }
                for s in product.sizes.all()
            ],

            "colors": [
                {
                    "id": c.id,
                    "color_name": c.color_name,
                    "image": c.image.url if c.image else None
                }
                for c in product.colors.all()
            ],

            "frames": [
                {
                    "id": f.id,
                    "name": f.name,
                    # "extra_price": str(f.extra_price) if f.extra_price is not None else None,
                    "extra_price": (
                    convert_price(
                        f.extra_price,
                        currency
                    )
                    if f.extra_price is not None
                    else None
                ),
                    "image": f.image.url if getattr(f, "image", None) else None
                }
                for f in product.frames.all()
            ],

            "materials": [
                {
                    "id": m.id,
                    "name": m.name,
                    "description": m.description,
                    # "extra_price": str(m.extra_price) if m.extra_price is not None else None
                    "extra_price": (
                        convert_price(
                            m.extra_price,
                            currency
                        )
                        if m.extra_price is not None
                        else None
                    )
                    
                }
                for m in product.materials.all()
            ],

            "average_rating": round(rating_summary["avg_rating"] or 0, 1),
            "review_count": rating_summary["total_reviews"],

            "reviews": [
                {
                    "id": r.id,
                    "name": r.name,
                    "rating": r.rating,
                    "comment": r.comment,
                    "created_at": r.created_at,
                }
                for r in reviews_qs
            ]
        }

        return JsonResponse(data, status=200)

    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)


from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["GET"])
def view_coupons(request):
    coupons = Coupon.objects.all()

    data = [
        {
            "id": coupon.id,
            "code": coupon.code,
            "discount": coupon.discount,
            "expiration_date": coupon.expiration_date,
            "created_at": coupon.created_at,
        }
        for coupon in coupons
    ]

    return JsonResponse({"coupons": data}, status=200)


def list_subcategories(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)

    subs = SubCategory.objects.all().order_by("name")

    data = [
        {"id": s.id, "name": s.name}
        for s in subs
    ]

    return JsonResponse(data, safe=False)


@require_http_methods(["GET"])
def view_brands(request):
    search = request.GET.get("search", "")

    brands = Brand.objects.filter(
        Q(name__icontains=search)
    ).order_by("-id")

    data = [
        {
            "id": brand.id,
            "name": brand.name,
            "created_at": brand.created_at
        }
        for brand in brands
    ]

    return JsonResponse({"brands": data}, status=200)


@require_http_methods(["GET"])
def view_categories(request):
    search = request.GET.get("search", "")

    categories = Category.objects.filter(
        Q(name__icontains=search)
    ).order_by("priority")

    data = [
        {
            "id": category.id,
            "name": category.name,
            "description":category.description,
            "image": category.image.url if category.image else None,
            "created_at": category.created_at,
            "priority":category.priority,
            "subdescription": category.subdescription
        }
        for category in categories
    ]

    return JsonResponse({"categories": data}, status=200)

@api_view(["POST"])
@permission_classes([AllowAny])
def apply_coupon(request):
    order_id = request.data.get("order_id")
    code = request.data.get("coupon_code")

    if not order_id or not code:
        return Response({"error": "order_id and coupon_code required"}, status=400)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)

    ok, msg = apply_coupon_to_order(order, code)

    if not ok:
        return Response({"error": msg}, status=400)

    return Response({
        "message": msg,
        "new_total": order.total_amount,
        "discount": order.discount_amount
    })


import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings
from ChronasAdmin.models import Order
from .currency import convert_amount

class CreateZiinaPayment(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            order_id = request.data.get("order_id")

            if not order_id:
                return Response({"error": "order_id required"}, status=400)

            order = Order.objects.get(id=order_id)

            # same security logic you used
            if request.user.is_authenticated:
                if order.user != request.user:
                    return Response({"error": "Unauthorized order access"}, status=403)

            else:
                guest_id = request.headers.get("X-Guest-Id")

                if not guest_id or order.guest_id != guest_id:
                    return Response({"error": "Unauthorized guest order"}, status=403)

            url = "https://api-v2.ziina.com/api/payment_intent"

            headers = {
                "Authorization": f"Bearer {settings.ZIINA_API_KEY}",
                "Content-Type": "application/json"
            }
            currency = order.currency.upper()
            if currency != "AED":
                return Response(
                    {
                        "error": "Ziina currently supports AED payments only"
                    },
                    status=400
                )
            payload = {
                "amount": convert_amount(
                    order.total_amount,
                    currency
                ),

                "currency_code": currency,

                "message": f"Order {order.id}",

                "metadata": {
                    "order_id": str(order.id)
                }
            }

            response = requests.post(url, json=payload, headers=headers)

            data = response.json()

            if response.status_code not in [200, 201]:
                return Response(
                    {
                        "error": data
                    },
                    status=response.status_code
                )

            return Response({
                "payment_url": data.get("redirect_url")
            })

        except Order.DoesNotExist:
            return Response({"error": "Invalid order"}, status=404)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
        


# user/views.py

from django.http import JsonResponse
from ChronasAdmin.models import FineArtSize, Frame, Material
from ChronusUser.currency import convert_price

def calculate_price(request):

    size_id = request.GET.get("size")
    frame_id = request.GET.get("frame")
    material_id = request.GET.get("material")

    currency = request.GET.get(
        "currency",
        "USD"
    ).upper()

    size = FineArtSize.objects.get(id=size_id)
    frame = Frame.objects.get(id=frame_id)
    material = Material.objects.get(id=material_id)

    price = size.price + frame.extra_price + material.extra_price

    return JsonResponse({
        "price": convert_price(
            price,
            currency
        ),
        "currency": currency
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def track_order(request, order_id):

    order = get_object_or_404(Order, id=order_id)

    return Response({

        "order_id": order.id,

        "status": order.status,

        "currency": order.currency,

        "total_amount": convert_price(
            order.total_amount,
            order.currency
        ),

        "tracking_link": order.tracking_link,

        "tracking_number": order.tracking_number,

        "carrier": order.carrier,

        "shipped_at": order.shipped_at
    })




# class CreateTabbyPayment(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         try:
#             order_id = request.data.get("order_id")

#             if not order_id:
#                 return Response(
#                     {"error": "order_id required"},
#                     status=400
#                 )

#             order = Order.objects.get(id=order_id)

#             # SECURITY CHECK
#             if request.user.is_authenticated:

#                 if order.user != request.user:
#                     return Response(
#                         {"error": "Unauthorized order access"},
#                         status=403
#                     )

#             else:
#                 guest_id = request.headers.get("X-Guest-Id")

#                 print("Order Guest ID:", order.guest_id)
#                 print("Header Guest ID:", guest_id)

#                 if not guest_id or order.guest_id != guest_id:
#                     return Response(
#                         {"error": "Unauthorized guest order"},
#                         status=403
#                     )

#             url = "https://api.tabby.ai/api/v2/checkout"

#             headers = {
#                 "Authorization": f"Bearer {settings.TABBY_SECRET_KEY}",
#                 "Content-Type": "application/json"
#             }

#             payload = {
#                 "payment": {
#                     "amount": str(order.total_amount),
#                     "currency": "AED",
#                     "description": f"Order #{order.id}",
#                     "buyer": {
#                         "email": order.email,
#                         "phone": order.phone,
#                         "name": request.data.get("name", "Customer")
#                     },
#                     "order": {
#                         "reference_id": str(order.id),
#                         "items": [
#                             {
#                                 "title": item.product.name if item.product else "Product",
#                                 "quantity": item.quantity,
#                                 "unit_price": str(item.price),
#                                 "category": (
#                                     item.product.category.name
#                                     if item.product and item.product.category
#                                     else "General"
#                                 )
#                             }
#                             for item in order.items.all()
#                         ]
#                     },
#                     "shipping_address": {
#                         "address": order.shipping_address,
#                         "city": request.data.get("city", ""),
#                         "country": request.data.get("country", "AE")
#                     },
#                     "buyer_history": {
#                         "registered_since": "2024-01-01",
#                         "loyalty_level": 0
#                     }
#                 },
#                 "lang": "en",
#                 "merchant_code": "VVAE",
#                 "merchant_urls": {
#                     "success": "https://chronosgallery.com/payment-success",
#                     "cancel": "https://chronosgallery.com/payment-cancel",
#                     "failure": "https://chronosgallery.com/payment-failure"
#                 }
#             }

#             print("TABBY URL:", url)
#             print("TABBY PAYLOAD:", payload)

#             response = requests.post(
#                 url,
#                 json=payload,
#                 headers=headers,
#                 timeout=30
#             )

#             print("STATUS:", response.status_code)
#             print("RESPONSE TEXT:")
#             print(response.text)

#             try:
#                 data = response.json()
#             except Exception:
#                 return Response(
#                     {
#                         "error": "Tabby returned non-JSON response",
#                         "status_code": response.status_code,
#                         "response": response.text
#                     },
#                     status=500
#                 )

#             if response.status_code not in [200, 201]:
#                 return Response(
#                     {
#                         "error": data
#                     },
#                     status=400
#                 )

#             return Response({
#                 "payment_id": data.get("id"),
#                 "payment_url": data.get("configuration", {})
#                                   .get("available_products", {})
#                                   .get("installments", {})
#                                   .get("web_url"),
#                 "full_response": data
#             })

#         except Order.DoesNotExist:
#             return Response(
#                 {"error": "Invalid order"},
#                 status=404
#             )

#         except Exception as e:
#             import traceback
#             traceback.print_exc()

#             return Response(
#                 {"error": str(e)},
#                 status=500
#             )
        
# class CreateTabbyPayment(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         try:
#             order_id = request.data.get("order_id")

#             if not order_id:
#                 return Response(
#                     {"error": "order_id required"},
#                     status=400
#                 )

#             order = Order.objects.get(id=order_id)

#             # SECURITY CHECK
#             if request.user.is_authenticated:

#                 if order.user != request.user:
#                     return Response(
#                         {"error": "Unauthorized order access"},
#                         status=403
#                     )

#             else:
#                 guest_id = request.headers.get("X-Guest-Id")

#                 print("Order Guest ID:", order.guest_id)
#                 print("Header Guest ID:", guest_id)

#                 if not guest_id or order.guest_id != guest_id:
#                     return Response(
#                         {"error": "Unauthorized guest order"},
#                         status=403
#                     )

#             url = "https://api.tabby.ai/api/v2/checkout"

#             headers = {
#                 "Authorization": f"Bearer {settings.TABBY_SECRET_KEY}",
#                 "Content-Type": "application/json"
#             }

#             payload = {
#                 "payment": {
#                     "amount": float(order.total_amount),
#                     "currency": "AED",
#                     "description": f"Order #{order.id}",
#                     "buyer": {
#                         "email": order.email,
#                         "phone": order.phone,
#                         "name": request.data.get("name", "Customer")
#                     },
#                     "order": {
#                         "reference_id": str(order.id),
#                         "items": [
#                             {
#                                 "title": item.product.name if item.product else "Product",
#                                 "quantity": item.quantity,
#                                 "unit_price": float(item.price),
#                                 "category": (
#                                     item.product.category.name
#                                     if item.product and item.product.category
#                                     else "General"
#                                 )
#                             }
#                             for item in order.items.all()
#                         ]
#                     },
#                     "shipping_address": {
#                         "address": order.shipping_address,
#                         "city": request.data.get("city", ""),
#                         "country": request.data.get("country", "AE")
#                     },
#                     "buyer_history": {
#                         "registered_since": "2024-01-01",
#                         "loyalty_level": 0
#                     }
#                 },
#                 "lang": "en",
#                 "merchant_code": "VVAE",
#                 "merchant_urls": {
#                     "success": "https://chronosgallery.com/payment-success",
#                     "cancel": "https://chronosgallery.com/payment-cancel",
#                     "failure": "https://chronosgallery.com/payment-failure"
#                 }
#             }

#             # DEBUGGING
#             if not settings.TABBY_SECRET_KEY:
#                 return Response(
#                     {"error": "TABBY_SECRET_KEY is empty"},
#                     status=500
#                 )

#             print("\n================ TABBY REQUEST ================")
#             print("URL:")
#             print(url)

#             print("\nSECRET KEY:")
#             print(repr(settings.TABBY_SECRET_KEY))

#             print("\nHEADERS:")
#             print(headers)

#             print("\nPAYLOAD:")
#             print(payload)

#             response = requests.post(
#                 url,
#                 json=payload,
#                 headers=headers,
#                 timeout=30
#             )

#             print("\n================ TABBY RESPONSE ================")

#             print("STATUS CODE:")
#             print(response.status_code)

#             print("\nRESPONSE HEADERS:")
#             print(dict(response.headers))

#             print("\nRESPONSE BODY:")
#             print(repr(response.text))

#             print("\n================================================")

#             try:
#                 data = response.json()
#             except Exception as json_error:
#                 print("JSON PARSE ERROR:", str(json_error))

#                 return Response(
#                     {
#                         "error": "Tabby returned non-JSON response",
#                         "status_code": response.status_code,
#                         "response": response.text,
#                         "headers": dict(response.headers)
#                     },
#                     status=500
#                 )

#             if response.status_code not in [200, 201]:
#                 return Response(
#                     {
#                         "error": data,
#                         "status_code": response.status_code
#                     },
#                     status=400
#                 )

#             return Response({
#                 "payment_id": data.get("id"),
#                 "payment_url": data.get("configuration", {})
#                                   .get("available_products", {})
#                                   .get("installments", {})
#                                   .get("web_url"),
#                 "full_response": data
#             })

#         except Order.DoesNotExist:
#             return Response(
#                 {"error": "Invalid order"},
#                 status=404
#             )

#         except Exception as e:
#             import traceback
#             traceback.print_exc()

#             return Response(
#                 {"error": str(e)},
#                 status=500
#             )
        
from .currency import convert_amount

class CreateTabbyPayment(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            order_id = request.data.get("order_id")

            if not order_id:
                return Response(
                    {"error": "order_id required"},
                    status=400
                )

            order = Order.objects.get(id=order_id)

            # SECURITY CHECK
            if request.user.is_authenticated:

                if order.user != request.user:
                    return Response(
                        {"error": "Unauthorized order access"},
                        status=403
                    )

            else:
                guest_id = request.headers.get("X-Guest-Id")

                if not guest_id or order.guest_id != guest_id:
                    return Response(
                        {"error": "Unauthorized guest order"},
                        status=403
                    )

            currency = order.currency.upper()

            # Remove this block if your Tabby account supports multiple currencies
            if currency != "AED":
                return Response(
                    {
                        "error": "Tabby currently supports AED payments only"
                    },
                    status=400
                )

            total_amount = round(
                convert_amount(
                    order.total_amount,
                    currency
                ) / 100,
                2
            )

            url = "https://api.tabby.ai/api/v2/checkout"

            headers = {
                "Authorization": f"Bearer {settings.TABBY_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "payment": {
                    "amount": total_amount,
                    "currency": currency,
                    "description": f"Order #{order.id}",

                    "buyer": {
                        "email": order.email,
                        "phone": order.phone,
                        "name": request.data.get(
                            "name",
                            "Customer"
                        )
                    },

                    "order": {
                        "reference_id": str(order.id),

                        "items": [
                            {
                                "title": (
                                    item.product.name
                                    if item.product
                                    else "Product"
                                ),

                                "quantity": item.quantity,

                                "unit_price": round(
                                    convert_amount(
                                        item.price,
                                        currency
                                    ) / 100,
                                    2
                                ),

                                "category": (
                                    item.product.category.name
                                    if item.product
                                    and item.product.category
                                    else "General"
                                )
                            }
                            for item in order.items.all()
                        ]
                    },

                    "shipping_address": {
                        "address": order.shipping_address,
                        "city": request.data.get("city", ""),
                        "country": request.data.get("country", "AE")
                    },

                    "buyer_history": {
                        "registered_since": "2024-01-01",
                        "loyalty_level": 0
                    }
                },

                "lang": "en",

                "merchant_code": "VVAE",

                "merchant_urls": {
                    "success": "https://chronosgallery.com/payment-success",
                    "cancel": "https://chronosgallery.com/payment-cancel",
                    "failure": "https://chronosgallery.com/payment-failure"
                }
            }

            # DEBUG
            print("\n=========== TABBY DEBUG ===========")
            print("TABBY_SECRET_KEY:", repr(settings.TABBY_SECRET_KEY))
            print("CURRENCY:", currency)
            print("TOTAL AMOUNT:", total_amount)
            print("PAYLOAD:", payload)
            print("===================================\n")

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )

            print("TABBY STATUS:", response.status_code)
            print("TABBY RESPONSE:", response.text)

            try:
                data = response.json()
            except Exception:
                return Response(
                    {
                        "error": "Tabby returned non-JSON response",
                        "status_code": response.status_code,
                        "response": response.text
                    },
                    status=500
                )

            if response.status_code not in [200, 201]:
                return Response(
                    {
                        "error": data,
                        "status_code": response.status_code
                    },
                    status=400
                )

            return Response({
                "payment_id": data.get("id"),
                "payment_url": data.get("configuration", {})
                                   .get("available_products", {})
                                   .get("installments", {})
                                   .get("web_url"),
                "full_response": data
            })

        except Order.DoesNotExist:
            return Response(
                {"error": "Invalid order"},
                status=404
            )

        except Exception as e:
            import traceback
            traceback.print_exc()

            return Response(
                {"error": str(e)},
                status=500
            )
        

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.contrib.auth.models import User

@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get("email")

    if not email:
        return Response(
            {"error": "Email is required"},
            status=400
        )

    user = User.objects.filter(email=email).first()

    if not user:
        return Response(
            {"message": "If the email exists, a reset link has been sent"}
        )

    uid = urlsafe_base64_encode(
        force_bytes(user.pk)
    )

    token = default_token_generator.make_token(
        user
    )

    reset_link = (
        f"https://chronosgallery.com/reset-password/"
        f"{uid}/{token}/"
    )

    send_mail(
        subject="Reset Your Password",
        message=f"""
Click the link below to reset your password:

{reset_link}

If you did not request this, ignore this email.
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return Response({
        "message": "Password reset link sent"
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    uid = request.data.get("uid")
    token = request.data.get("token")
    password = request.data.get("password")

    if not uid or not token or not password:
        return Response(
            {"error": "uid, token and password required"},
            status=400
        )

    try:
        user_id = urlsafe_base64_decode(
            uid
        ).decode()

        user = User.objects.get(
            pk=user_id
        )

    except Exception:
        return Response(
            {"error": "Invalid reset link"},
            status=400
        )

    if not default_token_generator.check_token(
        user,
        token
    ):
        return Response(
            {"error": "Invalid or expired token"},
            status=400
        )

    user.set_password(password)
    user.save()

    return Response({
        "message": "Password updated successfully"
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_address(request):

    if request.data.get("is_default"):

        Address.objects.filter(
            user=request.user
        ).update(
            is_default=False
        )

    address = Address.objects.create(
        user=request.user,
        full_name=request.data.get("full_name"),
        phone=request.data.get("phone"),
        address_line_1=request.data.get("address_line_1"),
        address_line_2=request.data.get("address_line_2"),
        city=request.data.get("city"),
        state=request.data.get("state"),
        country=request.data.get("country"),
        postal_code=request.data.get("postal_code"),
        is_default=request.data.get(
            "is_default",
            False
        )
    )

    return Response({
        "message": "Address added",
        "id": address.id
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_addresses(request):

    addresses = Address.objects.filter(
        user=request.user
    )

    data = []

    for address in addresses:
        data.append({
            "id": address.id,
            "full_name": address.full_name,
            "phone": address.phone,
            "address_line_1": address.address_line_1,
            "address_line_2": address.address_line_2,
            "city": address.city,
            "state": address.state,
            "country": address.country,
            "postal_code": address.postal_code,
            "is_default": address.is_default
        })

    return Response(data)

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_address(request, address_id):

    address = Address.objects.get(
        id=address_id,
        user=request.user
    )

    if request.data.get("is_default"):

        Address.objects.filter(
            user=request.user
        ).exclude(
            id=address.id
        ).update(
            is_default=False
        )

    for field in [
        "full_name",
        "phone",
        "address_line_1",
        "address_line_2",
        "city",
        "state",
        "country",
        "postal_code"
    ]:
        if field in request.data:
            setattr(
                address,
                field,
                request.data[field]
            )

    if "is_default" in request.data:
        address.is_default = request.data["is_default"]

    address.save()

    return Response({
        "message": "Address updated"
    })


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_address(request, address_id):

    address = Address.objects.get(
        id=address_id,
        user=request.user
    )

    address.delete()

    return Response({
        "message": "Address deleted"
    })