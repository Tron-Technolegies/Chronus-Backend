"""
Isolated settings for the automated test-suite.

    python manage.py test --settings=ProjectChronas.settings_test

* Replaces the PostgreSQL database with in-memory SQLite, so the tests can
  NEVER connect to (or write to) the real database.
* Uses in-memory file storage and the local-memory e-mail backend, so nothing
  is uploaded or sent.
* Everything else (JWT, DRF, throttling, installed apps) is inherited from
  the real settings so the tests exercise the real configuration.
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "chronus-tests",
    }
}
