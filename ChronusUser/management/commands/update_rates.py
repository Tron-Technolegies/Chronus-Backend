from django.core.management.base import BaseCommand

from ChronusUser.currency import update_exchange_rates


class Command(BaseCommand):

    help = "Update exchange rates"

    def handle(self, *args, **kwargs):

        success = update_exchange_rates()

        if success:
            self.stdout.write(
                self.style.SUCCESS(
                    "Exchange rates updated successfully"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Failed to update exchange rates"
                )
            )