from django.core.mail import send_mail
from django.conf import settings


def send_shipment_email(order):

    send_mail(
        subject=f"Your Order #{order.id} Has Been Shipped",
        message=f"""
Hello,

Good news! Your order has been shipped.

Order ID: {order.id}

Carrier: {order.carrier}

Tracking Number:
{order.tracking_number}

Track Shipment:
{order.tracking_link}

Thank you for shopping with Chronos Gallery.
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        fail_silently=False,
    )