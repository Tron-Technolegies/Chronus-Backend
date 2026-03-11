EXCHANGE_RATES = {
    "usd": 1,
    "aed": 3.67,
    "eur": 0.92,
    "gbp": 0.78,
    "inr": 83
}

def convert_amount(amount, currency):
    currency = currency.lower()

    rate = EXCHANGE_RATES.get(currency, 1)

    converted = float(amount) * rate

    return int(converted * 100)  