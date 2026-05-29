import requests
from django.conf import settings


def create_unified_shipment(order):

    url = "https://api.your-unified-provider.com/create-shipment"

    payload = {
        "order_id": order.id,

        "customer": {
            "name": order.user.username if order.user else "Guest",
            "email": order.email,
            "phone": order.phone,
        },

        "shipping_address": order.shipping_address,

        "items": [
            {
                "name": item.product.name,
                "quantity": item.quantity,
                "price": float(item.price)
            }
            for item in order.items.all()
        ]
    }

    headers = {
        "Authorization": f"Bearer {settings.UNIFIED_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers
    )

    response.raise_for_status()

    return response.json()