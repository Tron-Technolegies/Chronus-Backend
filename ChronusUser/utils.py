from django.utils import timezone
from decimal import Decimal
from .models import Coupon

def apply_coupon_to_order(order, code):
    try:
        coupon = Coupon.objects.get(code__iexact=code)
    except Coupon.DoesNotExist:
        return False, "Invalid coupon"

    if coupon.expiration_date < timezone.now().date():
        return False, "Coupon expired"

    discount = min(coupon.discount, order.total_amount)

    order.coupon = coupon
    order.discount_amount = discount
    order.total_amount = order.total_amount - discount
    order.save()

    return True, "Coupon applied"