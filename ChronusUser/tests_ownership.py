"""
Customer-side access tests (data ownership, login walls, no admin access).
The customer views are NOT modified by the RBAC work; these tests pin their
current behaviour.

Run with:  python manage.py test --settings=ProjectChronas.settings_test
"""
import json

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase

from ChronasAdmin.models import Order, Product
from ChronasAdmin.rbac_testkit import (
    PASSWORD,
    access_for,
    assert_isolated_database,
    bearer,
    expired_access_for,
    wrong_signature_access_for,
)
from ChronusUser.models import Address, Review


class CustomerBase(TestCase):
    @classmethod
    def setUpClass(cls):
        assert_isolated_database()
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            "alice@example.test", "alice@example.test", PASSWORD
        )
        cls.bob = User.objects.create_user(
            "bob@example.test", "bob@example.test", PASSWORD
        )
        cls.product = Product.objects.create(name="Watch", price=10)

    def setUp(self):
        cache.clear()
        self.client = Client(raise_request_exception=False)

    def as_user(self, user):
        return bearer(access_for(user))

    def send(self, method, path, user=None, body=None, extra=None):
        headers = extra if extra is not None else (
            self.as_user(user) if user else {}
        )
        return getattr(self.client, method)(
            f"/api/user/{path}",
            data=json.dumps(body or {}) if method != "get" else None,
            content_type="application/json",
            **headers,
        )


class OrderOwnershipTests(CustomerBase):
    def test_customer_sees_only_own_orders(self):
        mine = Order.objects.create(user=self.alice, email="alice@example.test")
        theirs = Order.objects.create(user=self.bob, email="bob@example.test")
        guest = Order.objects.create(guest_id="g1", email="guest@example.test")

        r = self.send("get", "orders/", self.alice)
        self.assertEqual(r.status_code, 200, r.content)
        ids = {o["id"] for o in r.json()["orders"]}
        self.assertEqual(ids, {mine.id})
        self.assertNotIn(theirs.id, ids)
        self.assertNotIn(guest.id, ids)

    def test_orders_require_login(self):
        self.assertEqual(self.send("get", "orders/").status_code, 401)


class AddressOwnershipTests(CustomerBase):
    def setUp(self):
        super().setUp()
        fields = dict(
            full_name="X", phone="1", address_line_1="a", city="c",
            state="s", country="AE", postal_code="1",
        )
        self.alice_addr = Address.objects.create(user=self.alice, **fields)
        self.bob_addr = Address.objects.create(user=self.bob, **fields)

    def test_list_only_returns_own_addresses(self):
        r = self.send("get", "addresses/", self.alice)
        self.assertEqual(r.status_code, 200)
        self.assertEqual({a["id"] for a in r.json()}, {self.alice_addr.id})

    def test_cannot_update_someone_elses_address(self):
        r = self.send(
            "put", f"addresses/{self.bob_addr.id}/update/", self.alice,
            {"city": "Hacked"},
        )
        self.assertNotEqual(r.status_code, 200)
        self.bob_addr.refresh_from_db()
        self.assertEqual(self.bob_addr.city, "c")

    def test_cannot_delete_someone_elses_address(self):
        r = self.send(
            "delete", f"addresses/{self.bob_addr.id}/delete/", self.alice
        )
        self.assertNotEqual(r.status_code, 200)
        self.assertTrue(Address.objects.filter(id=self.bob_addr.id).exists())

    def test_can_update_and_delete_own_address(self):
        r = self.send(
            "put", f"addresses/{self.alice_addr.id}/update/", self.alice,
            {"city": "Dubai"},
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.alice_addr.refresh_from_db()
        self.assertEqual(self.alice_addr.city, "Dubai")
        r = self.send(
            "delete", f"addresses/{self.alice_addr.id}/delete/", self.alice
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Address.objects.filter(id=self.alice_addr.id).exists())

    def test_address_endpoints_require_login(self):
        for method, path in [
            ("get", "addresses/"),
            ("post", "addresses/add/"),
            ("put", f"addresses/{self.alice_addr.id}/update/"),
            ("delete", f"addresses/{self.alice_addr.id}/delete/"),
        ]:
            self.assertEqual(self.send(method, path).status_code, 401, path)


class ProfileAndReviewTests(CustomerBase):
    def test_profile_requires_login_and_returns_own_data(self):
        self.assertEqual(self.send("get", "profile/").status_code, 401)
        r = self.send("get", "profile/", self.alice)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"alice@example.test", r.content)
        self.assertNotIn(b"bob@example.test", r.content)

    def test_cannot_edit_or_delete_someone_elses_review(self):
        review = Review.objects.create(
            product=self.product, user=self.bob, name="Bob", rating=5,
            comment="great",
        )
        r = self.send(
            "put", f"review/edit/{review.id}/", self.alice, {"comment": "x"}
        )
        self.assertEqual(r.status_code, 403)
        r = self.send("delete", f"review/delete/{review.id}/", self.alice)
        self.assertEqual(r.status_code, 403)
        review.refresh_from_db()
        self.assertEqual(review.comment, "great")

    def test_owner_can_edit_and_delete_review(self):
        review = Review.objects.create(
            product=self.product, user=self.bob, name="Bob", rating=5,
            comment="great",
        )
        r = self.send(
            "put", f"review/edit/{review.id}/", self.bob, {"comment": "ok"}
        )
        self.assertEqual(r.status_code, 200)
        r = self.send("delete", f"review/delete/{review.id}/", self.bob)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Review.objects.filter(id=review.id).exists())

    def test_review_edit_delete_require_login(self):
        self.assertEqual(self.send("put", "review/edit/1/").status_code, 401)
        self.assertEqual(self.send("delete", "review/delete/1/").status_code, 401)


class InvalidTokenTests(CustomerBase):
    def test_invalid_and_expired_tokens_get_401(self):
        bad = {
            "garbage": bearer("nope"),
            "expired": bearer(expired_access_for(self.alice)),
            "wrong_signature": bearer(wrong_signature_access_for(self.alice)),
        }
        for label, headers in bad.items():
            for path in ("orders/", "addresses/", "profile/"):
                with self.subTest(token=label, path=path):
                    r = self.send("get", path, extra=headers)
                    self.assertEqual(r.status_code, 401)


class PublicShoppingStillWorksTests(CustomerBase):
    """Guest/public APIs must stay reachable without credentials."""

    def test_public_browsing(self):
        for path in (
            "products/", f"products/{self.product.id}/", "view_brands/",
            "view_categories/", "view_coupons/", "subcategories/",
        ):
            with self.subTest(path=path):
                r = self.send("get", path)
                self.assertEqual(r.status_code, 200, r.content[:200])

    def test_guest_session_and_cart(self):
        r = self.send("post", "guest/create/")
        self.assertIn(r.status_code, (200, 201), r.content)
        guest_id = r.json()["guest_id"]
        r = self.client.get(
            "/api/user/cart/", HTTP_X_GUEST_ID=guest_id
        )
        self.assertNotIn(r.status_code, (401, 403, 404, 405), r.content[:200])

    def test_signup_and_login(self):
        r = self.send(
            "post", "signup/",
            body={"full_name": "Cara D", "email": "cara@example.test",
                  "password": PASSWORD},
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(set(r.json()["tokens"]), {"refresh", "access"})
        user = User.objects.get(email="cara@example.test")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        r = self.send(
            "post", "login/",
            body={"email": "cara@example.test", "password": PASSWORD},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            set(r.json()),
            {"message", "user_id", "email", "full_name", "tokens"},
        )

    def test_customer_token_cannot_reach_admin_api(self):
        r = self.client.get(
            "/api/admin/view_orders/", **self.as_user(self.alice)
        )
        self.assertEqual(r.status_code, 403)
