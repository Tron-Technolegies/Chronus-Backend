"""Shared fixtures/helpers for the access-control tests (not a test module)."""
import logging
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import connection
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

PASSWORD = "Str0ng-Test-Pass!"


def assert_isolated_database():
    """Hard stop if the tests are ever pointed at a real database."""
    assert connection.vendor == "sqlite", (
        "Tests must run on SQLite. Use "
        "--settings=ProjectChronas.settings_test"
    )
    assert "postgres" not in settings.DATABASES["default"]["ENGINE"]


def make_users():
    group, _ = Group.objects.get_or_create(name="Store Manager")

    def mk(username, **extra):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.test",
            password=PASSWORD,
            **extra,
        )

    users = {
        "customer": mk("customer"),
        "staff_plain": mk("staff_plain", is_staff=True),
        "group_not_staff": mk("group_not_staff"),
        "store_manager": mk("store_manager", is_staff=True),
        "super_admin": mk("super_admin", is_staff=True, is_superuser=True),
        "inactive_manager": mk(
            "inactive_manager", is_staff=True, is_active=False
        ),
    }
    users["group_not_staff"].groups.add(group)
    users["store_manager"].groups.add(group)
    users["inactive_manager"].groups.add(group)
    return users


def bearer(token):
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def access_for(user):
    # simplejwt logs a (harmless) warning when minting a token for an
    # inactive user, which is exactly what the inactive-user test needs.
    logging.disable(logging.CRITICAL)
    try:
        return str(AccessToken.for_user(user))
    finally:
        logging.disable(logging.NOTSET)


def expired_access_for(user):
    token = AccessToken.for_user(user)
    token.set_exp(lifetime=-timedelta(minutes=5))
    return str(token)


def wrong_signature_access_for(user):
    payload = AccessToken.for_user(user).payload
    return jwt.encode(payload, "x" * 64, algorithm="HS256")


def refresh_for(user):
    return str(RefreshToken.for_user(user))
