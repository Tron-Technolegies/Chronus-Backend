
import base64
import uuid
import logging
import requests

from decimal import Decimal
from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)


class DHLService:

    def __init__(self):
        self.base_url = settings.DHL_BASE_URL.rstrip("/")
        self.username = settings.DHL_API_KEY
        self.password = settings.DHL_API_SECRET
        self.account_number = settings.DHL_ACCOUNT_NUMBER

    # --------------------------------------------------
    # AUTHENTICATION HEADERS
    # --------------------------------------------------

    def get_headers(self):

        if not self.username or not self.password:
            raise ValueError("DHL API credentials are missing.")

        credentials = f"{self.username}:{self.password}"

        encoded = base64.b64encode(
            credentials.encode()
        ).decode()

        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Message-Reference": str(uuid.uuid4()),
            "Message-Reference-Date": timezone.now().strftime(
                "%Y-%m-%dT%H:%M:%SGMT+00:00"
            )
        }

    # --------------------------------------------------
    # PRODUCT WEIGHT CALCULATION
    # --------------------------------------------------

    def calculate_weight(self, order):

        total_weight = Decimal("0.00")

        items = order.items.select_related("product").all()

        if not items.exists():
            raise ValueError("Order has no items.")

        for item in items:

            if not item.product:
                raise ValueError(
                    f"Product is missing for order item {item.id}."
                )

            product = item.product

            weight = product.weight or Decimal("0.00")

            if weight <= 0:
                raise ValueError(
                    f"Invalid weight for product: {product.name}"
                )

            if item.quantity <= 0:
                raise ValueError(
                    f"Invalid quantity for product: {product.name}"
                )

            total_weight += weight * item.quantity

        return total_weight.quantize(Decimal("0.01"))

    # --------------------------------------------------
    # PRODUCT DIMENSION CALCULATION
    # --------------------------------------------------

    def calculate_dimensions(self, order):

        length = Decimal("0.00")
        width = Decimal("0.00")
        height = Decimal("0.00")

        items = order.items.select_related("product").all()

        if not items.exists():
            raise ValueError("Order has no items.")

        for item in items:

            if not item.product:
                raise ValueError(
                    f"Product is missing for order item {item.id}."
                )

            product = item.product

            product_length = product.length
            product_width = product.width
            product_height = product.height

            if not all([
                product_length > 0,
                product_width > 0,
                product_height > 0
            ]):
                raise ValueError(
                    f"Invalid dimensions for product: {product.name}"
                )

            length = max(length, product_length)
            width = max(width, product_width)

            height += product_height * item.quantity

        return {
            "length": length.quantize(Decimal("0.01")),
            "width": width.quantize(Decimal("0.01")),
            "height": height.quantize(Decimal("0.01"))
        }

    # --------------------------------------------------
    # SHIPMENT DATA VALIDATION
    # --------------------------------------------------

    def validate_shipment_data(self, order):

        # Validate receiver details
        required_fields = {
            "receiver name": order.receiver_name,
            "address": order.address_line_1,
            "city": order.city,
            "postal code": order.postal_code,
            "country": order.country,
            "phone": order.phone,
            "email": order.email,
        }

        for field, value in required_fields.items():

            if not value or not str(value).strip():
                raise ValueError(
                    f"Missing required receiver {field}."
                )

        # Validate receiver country code
        country_code = order.country.strip()

        if (
            len(country_code) != 2
            or not country_code.isalpha()
        ):
            raise ValueError(
                "Receiver country must be a valid ISO 2-letter country code."
            )

        # Validate shipper configuration
        shipper_fields = {
            "DHL account number": self.account_number,
            "DHL API username": self.username,
            "DHL API password": self.password,
            "shipper address": settings.DHL_SHIPPER_ADDRESS,
            "shipper city": settings.DHL_SHIPPER_CITY,
            "shipper postal code": settings.DHL_SHIPPER_POSTAL_CODE,
            "shipper country": settings.DHL_SHIPPER_COUNTRY,
            "shipper name": settings.DHL_SHIPPER_NAME,
            "shipper phone": settings.DHL_SHIPPER_PHONE,
        }

        for field, value in shipper_fields.items():

            if not value or not str(value).strip():
                raise ValueError(
                    f"Missing DHL configuration: {field}."
                )

        shipper_country = settings.DHL_SHIPPER_COUNTRY.strip()

        if (
            len(shipper_country) != 2
            or not shipper_country.isalpha()
        ):
            raise ValueError(
                "DHL shipper country must be a valid ISO 2-letter code."
            )

        if not self.base_url:
            raise ValueError("DHL base URL is missing.")

        # Validate package weight and dimensions
        weight = self.calculate_weight(order)

        dimensions = self.calculate_dimensions(order)

        if weight <= 0:
            raise ValueError(
                "Shipment weight must be greater than zero."
            )

        for dimension, value in dimensions.items():

            if value <= 0:
                raise ValueError(
                    f"Shipment {dimension} must be greater than zero."
                )

        return weight, dimensions

    # --------------------------------------------------
    # BUILD SHIPMENT PAYLOAD
    # --------------------------------------------------

    def build_payload(self, order):

        weight, dimensions = self.validate_shipment_data(order)

        payload = {

            "plannedShippingDateAndTime":
                timezone.now().strftime(
                    "%Y-%m-%dT%H:%M:%SGMT+00:00"
                ),

            "pickup": {
                "isRequested": False
            },

            "productCode": "D",

            "accounts": [
                {
                    "typeCode": "shipper",
                    "number": self.account_number.strip()
                }
            ],

            "customerDetails": {

                "shipperDetails": {

                    "postalAddress": {

                        "addressLine1":
                            settings.DHL_SHIPPER_ADDRESS,

                        "cityName":
                            settings.DHL_SHIPPER_CITY,

                        "postalCode":
                            settings.DHL_SHIPPER_POSTAL_CODE,

                        "countryCode":
                            settings.DHL_SHIPPER_COUNTRY.strip().upper()

                    },

                    "contactInformation": {

                        "companyName":
                            settings.DHL_SHIPPER_NAME,

                        "fullName":
                            settings.DHL_SHIPPER_NAME,

                        "phone":
                            settings.DHL_SHIPPER_PHONE

                    }

                },

                "receiverDetails": {

                    "postalAddress": {

                        "addressLine1":
                            order.address_line_1,

                        "addressLine2":
                            order.address_line_2,

                        "cityName":
                            order.city,

                        "postalCode":
                            order.postal_code,

                        "countryCode":
                            order.country.strip().upper()

                    },

                    "contactInformation": {

                        "companyName":
                            order.receiver_name,

                        "fullName":
                            order.receiver_name,

                        "phone":
                            order.phone,

                        "email":
                            order.email

                    }

                }

            },

            "content": {

                "packages": [
                    {
                        "weight": float(weight),

                        "dimensions": {
                            "length": float(dimensions["length"]),
                            "width": float(dimensions["width"]),
                            "height": float(dimensions["height"])
                        }
                    }
                ],

                "description":
                    f"Order #{order.id}",

                "unitOfMeasurement":
                    "metric",

                "isCustomsDeclarable": False

            }

        }

        return payload

    # --------------------------------------------------
    # CREATE DHL SHIPMENT
    # --------------------------------------------------

    def create_shipment(self, order):

        url = f"{self.base_url}/shipments"

        payload = self.build_payload(order)

        try:

            response = requests.post(
                url,
                json=payload,
                headers=self.get_headers(),
                timeout=60
            )

            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:

            logger.error(
                "DHL shipment API returned HTTP %s.",
                response.status_code
            )

            # Keep the DHL error response available for debugging.
            raise Exception(
                f"DHL shipment creation failed: {response.text}"
            ) from e

        except requests.exceptions.RequestException as e:

            logger.exception("DHL shipment API request failed.")

            raise Exception(
                f"DHL connection error: {str(e)}"
            ) from e

    # --------------------------------------------------
    # GET AVAILABLE DHL PRODUCTS
    # --------------------------------------------------

    def get_available_products(self, order):

        weight = self.calculate_weight(order)

        dimensions = self.calculate_dimensions(order)

        if not settings.DHL_SHIPPER_COUNTRY:
            raise ValueError("DHL shipper country is missing.")

        if not settings.DHL_SHIPPER_CITY:
            raise ValueError("DHL shipper city is missing.")

        if not order.country or not order.city:
            raise ValueError(
                "Destination country and city are required."
            )

        url = f"{self.base_url}/products"

        params = {

            "accountNumber":
                self.account_number.strip(),

            "originCountryCode":
                settings.DHL_SHIPPER_COUNTRY.strip().upper(),

            "originCityName":
                settings.DHL_SHIPPER_CITY,

            "destinationCountryCode":
                order.country.strip().upper(),

            "destinationCityName":
                order.city,

            "weight":
                float(weight),

            "length":
                float(dimensions["length"]),

            "width":
                float(dimensions["width"]),

            "height":
                float(dimensions["height"]),

            "plannedShippingDate":
                timezone.localdate().strftime("%Y-%m-%d"),

            "isCustomsDeclarable":
                "false",

            "unitOfMeasurement":
                "metric"

        }

        try:

            response = requests.get(
                url,
                headers=self.get_headers(),
                params=params,
                timeout=60
            )

            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:

            logger.error(
                "DHL products API returned HTTP %s.",
                response.status_code
            )

            raise Exception(
                f"DHL product availability failed: {response.text}"
            ) from e

        except requests.exceptions.RequestException as e:

            logger.exception(
                "DHL products API request failed."
            )

            raise Exception(
                f"DHL connection error: {str(e)}"
            ) from e
