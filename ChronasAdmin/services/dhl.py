import base64
import uuid
import requests

from django.conf import settings
from django.utils import timezone
from datetime import datetime
import requests

class DHLService:

    def __init__(self):

        self.base_url = settings.DHL_BASE_URL
        self.username = settings.DHL_API_KEY
        self.password = settings.DHL_API_SECRET
        self.account_number = settings.DHL_ACCOUNT_NUMBER

    def get_headers(self):

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

    def calculate_weight(self, order):

        total_weight = 0

        for item in order.items.select_related(
            "product"
        ).all():

            total_weight += (
                float(item.product.weight)
                * item.quantity
            )

        return round(total_weight, 2)

    def calculate_dimensions(self, order):

        length = 0
        width = 0
        height = 0

        for item in order.items.select_related(
            "product"
        ).all():

            product = item.product

            length = max(
                length,
                float(product.length)
            )

            width = max(
                width,
                float(product.width)
            )

            height += (
                float(product.height)
                * item.quantity
            )

        return {

            "length": round(length, 2),

            "width": round(width, 2),

            "height": round(height, 2)
        }

    def build_payload(self, order):

        weight = self.calculate_weight(order)

        dimensions = self.calculate_dimensions(order)

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
                            settings.DHL_SHIPPER_COUNTRY

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
                            (
                                order.address_line_2
                                if order.address_line_2
                                else order.address_line_1
                            ),

                        "cityName":
                            order.city,

                        "postalCode":
                            order.postal_code,

                        "countryCode":
                            order.country

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

                        "weight": weight,

                        "dimensions": {

                            "length": dimensions["length"],

                            "width": dimensions["width"],

                            "height": dimensions["height"]

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

    def create_shipment(self, order):

        url = f"{self.base_url}/shipments"

        payload = self.build_payload(order)

        print("=" * 80)
        print("DHL REQUEST URL")
        print(url)

        print("=" * 80)
        print("DHL REQUEST PAYLOAD")
        print(payload)

        try:

            response = requests.post(

                url,

                json=payload,

                headers=self.get_headers(),

                timeout=60

            )

            print("=" * 80)
            print("DHL STATUS CODE")
            print(response.status_code)

            print("=" * 80)
            print("DHL RESPONSE")
            print(response.text)

            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError:

            print("=" * 80)
            print("DHL ERROR RESPONSE")
            print(response.text)

            raise Exception(response.text)

        except requests.exceptions.RequestException as e:

            raise Exception(str(e))
        
    
    def get_available_products(self, order):

        weight = self.calculate_weight(order)
        dimensions = self.calculate_dimensions(order)

        url = f"{self.base_url}/products"

        params = {
            "accountNumber": self.account_number.strip(),
            "originCountryCode": "AE",
            "originCityName": "Dubai",
            "destinationCountryCode": order.country,
            "destinationCityName": order.city,
            "weight": weight,
            "length": dimensions["length"],
            "width": dimensions["width"],
            "height": dimensions["height"],
            "plannedShippingDate": datetime.utcnow().strftime("%Y-%m-%d"),
            "isCustomsDeclarable": "false",
            "unitOfMeasurement": "metric"
        }

        response = requests.get(
            url,
            headers=self.get_headers(),
            params=params,
            timeout=60
        )

        print("=" * 80)
        print("PRODUCT API URL")
        print(response.url)

        print("=" * 80)
        print("STATUS")
        print(response.status_code)

        print("=" * 80)
        print("BODY")
        print(response.text)

        response.raise_for_status()

        return response.json()