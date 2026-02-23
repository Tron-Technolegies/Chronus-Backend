from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from ChronasAdmin.models import Product, Order, OrderItem
from .models import GuestSession, Cart, CartItem, Wishlist, Review

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
def get_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        guest_id = request.headers.get("guest_id")
        if not guest_id:
            raise Exception("guest_id header required for guest user")
        cart, _ = Cart.objects.get_or_create(guest_id=guest_id)
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
    items = CartItem.objects.filter(cart=cart)

    data = [
        {
            "product_id": item.product.id,
            "product": item.product.name,
            "price": item.product.price,
            "quantity": item.quantity,
            "total": item.quantity * item.product.price
        }
        for item in items
    ]
    return Response(data)


# ===============================
# WISHLIST
# ===============================
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
        if not guest_id:
            return Response({"error": "guest_id required"}, status=400)

        Wishlist.objects.get_or_create(guest_id=guest_id, product=product)

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


# ===============================
# CHECKOUT
# ===============================
@api_view(["POST"])
@permission_classes([AllowAny])
def checkout(request):
    cart = get_cart(request)
    items = CartItem.objects.filter(cart=cart)

    if not items.exists():
        return Response({"error": "Cart is empty"}, status=400)

    total = sum(i.quantity * i.product.price for i in items)

    guest_id = None
    if not request.user.is_authenticated:
        guest_id = request.headers.get("guest_id")
        if not guest_id:
            return Response({"error": "guest_id required"}, status=400)

    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        guest_id=guest_id,
        email=request.data.get("email"),
        phone=request.data.get("phone"),
        shipping_address=request.data.get("address"),
        total_amount=total,
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )

    items.delete()  # clear cart

    return Response({"order_id": order.id, "amount": total})


# ===============================
# USER ORDERS (AUTH)
# ===============================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_orders(request):
    orders = Order.objects.filter(user=request.user)

    data = [
        {
            "id": o.id,
            "total": o.total_amount,
            "status": o.status
        }
        for o in orders
    ]

    return Response(data)


# ===============================
# STRIPE PAYMENT
# ===============================
import stripe
from django.conf import settings
from rest_framework.views import APIView

stripe.api_key = settings.STRIPE_SECRET_KEY


class CreatePaymentIntentView(APIView):
    permission_classes = [AllowAny]  # allow guest

    def post(self, request):
        try:
            amount = request.data.get("amount")
            currency = request.data.get("currency", "usd")

            if not amount:
                return Response({"error": "Amount required"}, status=400)

            amount_in_cents = int(float(amount) * 100)

            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=currency.lower(),
                payment_method_types=["card"],
                metadata={
                    "user_id": request.user.id if request.user.is_authenticated else None,
                    "email": request.data.get("email"),
                }
            )

            return Response({
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id
            })

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)


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