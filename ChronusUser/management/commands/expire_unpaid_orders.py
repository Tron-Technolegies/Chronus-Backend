
from datetime import timedelta

import requests

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ChronasAdmin.models import Order, PaymentAttempt
from ChronusUser.views import release_order_stock


class Command(BaseCommand):
    help = "Safely restore stock for expired unpaid orders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=30,
            help="Expire unpaid orders older than this many minutes."
        )

    def verify_ziina_payment(self, attempt):
        """
        Check the actual Ziina payment status before releasing stock.
        Returns: completed, failed, cancelled, or unknown.
        """

        if not settings.ZIINA_API_KEY:
            self.stderr.write(
                self.style.ERROR("ZIINA_API_KEY is not configured.")
            )
            return "unknown"

        url = (
            "https://api-v2.ziina.com/api/payment_intent/"
            f"{attempt.payment_id}"
        )

        try:
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {settings.ZIINA_API_KEY}"
                },
                timeout=15
            )

            response.raise_for_status()
            data = response.json()

            status = data.get("status")

            self.stdout.write(
                f"Ziina payment {attempt.payment_id}: {status}"
            )

            if status == "completed":
                return "completed"

            if status == "failed":
                return "failed"

            if status == "canceled":
                return "cancelled"

            # pending, requires_user_action,
            # requires_payment_instrument, or unknown
            return "unknown"

        except (requests.RequestException, ValueError) as exc:
            self.stderr.write(
                self.style.ERROR(
                    f"Could not verify Ziina payment "
                    f"{attempt.payment_id}: {exc}"
                )
            )
            return "unknown"

    def handle(self, *args, **options):

        minutes = options["minutes"]

        if minutes <= 0:
            self.stderr.write("Timeout must be greater than zero.")
            return

        cutoff_time = timezone.now() - timedelta(minutes=minutes)

        order_ids = list(
            Order.objects.filter(
                payment_status="pending",
                stock_restored=False,
                created_at__lte=cutoff_time
            )
            .order_by("created_at")
            .values_list("id", flat=True)
        )

        self.stdout.write(
            f"Eligible unpaid orders: {len(order_ids)}"
        )

        processed = 0
        skipped = 0

        for order_id in order_ids:

            try:
                # Get pending Ziina attempts before taking DB locks.
                ziina_attempts = list(
                    PaymentAttempt.objects.filter(
                        order_id=order_id,
                        gateway="ziina",
                        status="pending"
                    )
                )

                unsafe_to_expire = False

                for attempt in ziina_attempts:

                    provider_status = self.verify_ziina_payment(attempt)

                    if provider_status == "completed":
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipped order {order_id}: "
                                "Ziina confirms payment completed. "
                                "Waiting for webhook processing."
                            )
                        )
                        unsafe_to_expire = True
                        break

                    if provider_status == "unknown":
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipped order {order_id}: "
                                "Ziina payment status could not be confirmed."
                            )
                        )
                        unsafe_to_expire = True
                        break

                    if provider_status in ["failed", "cancelled"]:

                        with transaction.atomic():

                            locked_order = Order.objects.select_for_update().get(
                                id=order_id
                            )

                            locked_attempt = PaymentAttempt.objects.select_for_update().get(
                                id=attempt.id
                            )

                            if (
                                locked_attempt.status == "pending"
                                and locked_order.payment_status == "pending"
                                and not locked_order.stock_restored
                            ):
                                locked_attempt.status = provider_status
                                locked_attempt.save(
                                    update_fields=["status"]
                                )

                if unsafe_to_expire:
                    skipped += 1
                    continue

                # Final database checks and stock restoration.
                with transaction.atomic():

                    order = Order.objects.select_for_update().get(
                        id=order_id
                    )

                    if (
                        order.payment_status != "pending"
                        or order.stock_restored
                    ):
                        skipped += 1
                        continue

                    # Do not expire while ANY payment attempt is unresolved.
                    has_unresolved_attempt = order.payment_attempts.filter(
                        status__in=["pending", "authorized", "completed"]
                    ).exists()

                    if has_unresolved_attempt:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipped order {order_id}: "
                                "another payment attempt is unresolved."
                            )
                        )
                        skipped += 1
                        continue

                    restored = release_order_stock(order.id)

                    if restored:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Stock restored for order {order.id}"
                            )
                        )
                        processed += 1
                    else:
                        skipped += 1

            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"Error processing order {order_id}: {exc}"
                    )
                )
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. Restored: {processed}, Skipped: {skipped}"
            )
        )
