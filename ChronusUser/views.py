from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from ChronasAdmin.models import Product, Order, OrderItem
from .models import GuestSession, Cart, CartItem, Wishlist, Review
import uuid


@api_view(["POST"])
def create_guest(request):
    guest = GuestSession.objects.create()
    return Response({"guest_id": str(guest.guest_id)})


def get_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        guest_id = request.headers.get("guest_id")
        cart, _ = Cart.objects.get_or_create(guest_id=guest_id)
    return cart


@api_view(["POST"])
def add_to_cart(request):
    product_id = request.data["product_id"]
    qty = int(request.data.get("quantity", 1))

    cart = get_cart(request)
    product = Product.objects.get(id=product_id)

    item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        item.quantity += qty
    item.save()

    return Response({"message": "Added to cart"})


@api_view(["GET"])
def view_cart(request):
    cart = get_cart(request)
    items = CartItem.objects.filter(cart=cart)
    data = [
        {
            "product": item.product.name,
            "price": item.product.price,
            "quantity": item.quantity,
            "total": item.quantity * item.product.price
        }
        for item in items
    ]
    return Response(data)


@api_view(["POST"])
def add_to_wishlist(request):
    product = Product.objects.get(id=request.data["product_id"])
    if request.user.is_authenticated:
        Wishlist.objects.get_or_create(user=request.user, product=product)
    else:
        Wishlist.objects.get_or_create(guest_id=request.headers.get("guest_id"), product=product)

    return Response({"message": "Added to wishlist"})


@api_view(["POST"])
def add_review(request):
    Review.objects.create(
        product_id=request.data["product_id"],
        user=request.user if request.user.is_authenticated else None,
        name=request.data.get("name", "Guest"),
        rating=request.data["rating"],
        comment=request.data["comment"]
    )
    return Response({"message": "Review added"})


@api_view(["POST"])
def checkout(request):
    cart = get_cart(request)
    items = CartItem.objects.filter(cart=cart)

    total = sum(i.quantity * i.product.price for i in items)

    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        guest_id=request.headers.get("guest_id"),
        email=request.data["email"],
        phone=request.data["phone"],
        shipping_address=request.data["address"],
        total_amount=total,
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )

    items.delete()  # empty cart

    return Response({"order_id": order.id, "amount": total})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_orders(request):
    orders = Order.objects.filter(user=request.user)
    return Response([{"id": o.id, "total": o.total_amount, "status": o.status} for o in orders])

import stripe
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

stripe.api_key = settings.STRIPE_SECRET_KEY


class CreatePaymentIntentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            amount = request.data.get("amount")
            currency = request.data.get("currency")

            if not amount or not currency:
                return Response(
                    {"error": "Amount and currency are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Stripe expects amount in smallest currency unit
            amount_in_cents = int(float(amount) * 100)

            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=currency.lower(),
                payment_method_types=["card"],
                metadata={
                    "user_id": request.user.id,
                    "email": request.user.email,
                }
            )

            return Response({
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id
            }, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


