from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import APIView, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
import stripe
from ChronasAdmin.models import Coupon, Product, Order, OrderItem, SubCategory
from ChronusUser.utils import apply_coupon_to_order
from .models import GuestSession, Cart, CartItem, Wishlist, Review
from ChronasAdmin.models import Category, Brand, Product, Order, Coupon, SubCategory
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Count
from ChronasAdmin.models import ProductColor
# ===============================
# GUEST SESSION
# ===============================
@api_view(["POST"])
@permission_classes([AllowAny])
def create_guest(request):
    guest = GuestSession.objects.create()
    return Response({"guest_id": str(guest.guest_id)})


# ===============================
# CART HELPERS
# ===============================
# def get_cart(request):
#     if request.user.is_authenticated:
#         cart, _ = Cart.objects.get_or_create(user=request.user)
#     else:
#         guest_id = (
#             request.headers.get("x-guest-id")
#             or request.META.get("HTTP_X_GUEST_ID")
#         )
#         if not guest_id:
#             raise Exception("guest_id header required for guest user")

#         cart, _ = Cart.objects.get_or_create(guest_id=guest_id)

#     return cart

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
    qty = int(request.data.get("quantity", 1))

    if not product_id:
        return Response({"error": "product_id required"}, status=400)

    if qty <= 0:
        return Response({"error": "Invalid quantity"}, status=400)

    cart = get_cart(request)
    product = get_object_or_404(Product, id=product_id)

    item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        item.quantity += qty
    else:
        item.quantity = qty

    item.save()

    return Response({"message": "Added to cart"})


@api_view(["GET"])
@permission_classes([AllowAny])
def view_cart(request):
    cart = get_cart(request)
    # items = CartItem.objects.select_related("product").filter(cart=cart)
    items = CartItem.objects.select_related("product").only(
    "quantity",
    "product__id",
    "product__name",
    "product__price",
    "product__image"
).filter(cart=cart)
    subtotal = 0

    data = []

    for item in items:
        total = item.quantity * item.product.price
        subtotal += total

        data.append({
            "product_id": item.product.id,
            "product": item.product.name,
            "price": item.product.price,
            "image": item.product.image.url if item.product.image else None,
            "quantity": item.quantity,
            "total": total
        })

    return Response({
        "items": data,
        "subtotal": subtotal
    })

@api_view(["DELETE"])
@permission_classes([AllowAny])
def remove_from_cart(request, product_id):
    cart = get_cart(request)

    try:
        item = CartItem.objects.get(cart=cart, product_id=product_id)
        item.delete()
        return Response({"message": "Item removed"})
    except CartItem.DoesNotExist:
        return Response({"error": "Item not found in cart"}, status=404)
    
# @api_view(["DELETE"])
# @permission_classes([AllowAny])
# def clear_cart(request):
#     cart = get_cart(request)
#     CartItem.objects.filter(cart=cart).delete()
#     return Response({"message": "Cart cleared"})

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


@api_view(["POST"])
@permission_classes([AllowAny])
def checkout(request):
    cart = get_cart(request)

    items = CartItem.objects.select_related("product").filter(cart=cart)

    if not items.exists():
        return Response({"error": "Cart is empty"}, status=400)

    total = 0
    for i in items:
        total += i.quantity * i.product.price

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
    )

    order_items = [
        OrderItem(
            order=order,
            product=i.product,
            quantity=i.quantity,
            price=i.product.price
        )
        for i in items
    ]
    OrderItem.objects.bulk_create(order_items)

  
    return Response({"order_id": order.id, "amount": total})

# ===============================
# USER ORDERS (AUTH)
# ===============================
# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def my_orders(request):
#     orders = Order.objects.filter(user=request.user)

#     data = [
#         {
#             "id": o.id,
#             "total": o.total_amount,
#             "status": o.status
#         }
#         for o in orders
#     ]

#     return Response(data)

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
                "price": str(item.price),
            })

        data.append({
            "id": order.id,
            "status": order.status,
            "total_amount": str(order.total_amount),
            "created_at": order.created_at,
            "items": items
        })

    return Response({"orders": data})

from .currency import convert_amount

class CreatePaymentIntentView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            order_id = request.data.get("order_id")
            currency = request.data.get("currency", "usd").lower()
            
            if not order_id:
                return Response({"error": "order_id required"}, status=400)

            order = Order.objects.get(id=order_id)

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

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
@csrf_exempt
@require_http_methods(["GET"])
def view_products(request):

    category = request.GET.get("category")
    subcategory = request.GET.get("subcategory")
    search = request.GET.get("search")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 12))
    except ValueError:
        return JsonResponse({"error": "Invalid pagination values"}, status=400)

    offset = (page - 1) * limit

    products = Product.objects.select_related(
        "category", "subcategory", "brand"
    ).prefetch_related(
        "sizes",
        "colors",
        "gallery"
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

            "price": str(product.price),

            "stock": product.stock,

            "image": product.image.url if product.image else None,

            "created_at": product.created_at,

            "is_featured": product.is_featured,

            "is_best_seller": product.is_best_seller,

            "specification": product.specification,

            "sizes": [
                {
                    "size": s.size,
                    "price": str(s.price)
                }
                for s in product.sizes.all()
            ],

            "colors": [
                {
                    "color_name": c.color_name,
                    "image": c.image.url if c.image else None
                }
                for c in product.colors.all()
            ],

            "gallery": [
                img.image.url
                for img in product.gallery.all()
                if img.image
            ]
        })

    return JsonResponse({
        "page": page,
        "limit": limit,
        "total_products": total_products,
        "total_pages": (total_products + limit - 1) // limit,
        "products": data
    }, status=200)

@csrf_exempt
@require_http_methods(["GET"])
def view_single_product(request, product_id):
    try:
        product = Product.objects.select_related(
            "category", "subcategory", "brand"
        ).prefetch_related("gallery","sizes").get(id=product_id)
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
            } if getattr(product, "subcategory", None) else None,

            "brand": {
                "id": product.brand.id,
                "name": product.brand.name
            } if product.brand else None,

            "price": str(product.price),
            "description": product.description,
            "stock": product.stock,
            "image": product.image.url if product.image else None,
            "gallery": [img.image.url for img in product.gallery.all()],
            "is_featured": product.is_featured,
            "is_best_seller": product.is_best_seller,
            "created_at": product.created_at,
            "specification": product.specification,   

            "sizes": [                                
                {
                    "size": s.size,
                    "price": str(s.price)
                }
                for s in product.sizes.all()
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

            payload = {
                "amount": int(order.total_amount * 100),
                "currency_code": "AED",
                "message": f"Order {order.id}",
                "metadata": {
                    "order_id": str(order.id)
                }
            }

            response = requests.post(url, json=payload, headers=headers)

            data = response.json()

            return Response({
                "payment_url": data.get("redirect_url")
            })

        except Order.DoesNotExist:
            return Response({"error": "Invalid order"}, status=404)

        except Exception as e:
            return Response({"error": str(e)}, status=500)