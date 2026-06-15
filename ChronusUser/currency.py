import requests

from django.conf import settings
from .models import ExchangeRate


def update_exchange_rates():

    url = (
        f"https://v6.exchangerate-api.com/v6/"
        f"{settings.EXCHANGE_RATE_API_KEY}/latest/USD"
    )

    response = requests.get(url)

    if response.status_code != 200:
        return False

    data = response.json()

    if data.get("result") != "success":
        return False

    rates = data.get("conversion_rates", {})

    for currency, rate in rates.items():

        ExchangeRate.objects.update_or_create(
            currency=currency,
            defaults={
                "rate": rate
            }
        )

    return True


def get_rate(currency):

    currency = currency.upper()

    if currency == "USD":
        return 1

    exchange_rate = ExchangeRate.objects.filter(
        currency=currency
    ).first()

    if not exchange_rate:
        return 1

    return float(exchange_rate.rate)


# Stripe (returns cents)
def convert_amount(amount, currency):

    rate = get_rate(currency)

    converted = float(amount) * rate

    return int(converted * 100)


# Product display (returns normal price)
def convert_price(amount, currency):

    rate = get_rate(currency)

    return round(float(amount) * rate, 2)