"""
Access-control tests for every /api/admin/ route.

Run with:  python manage.py test --settings=ProjectChronas.settings_test

Authorization is asserted for each (route x actor). Requests use IDs that do
not exist, so an *authorised* call ends in 400/404 and never reaches DHL,
Cloudinary or any other external service; "authorised" therefore means
"status is neither 401 nor 403".
"""
import json
from datetime import date

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.test import Client, TestCase
from django.urls import get_resolver

from ChronasAdmin.models import (
    Brand,
    Coupon,
    Order,
    Product,
    ShippingPartner,
    Supplier,
)

from .rbac_testkit import (
    PASSWORD,
    access_for,
    assert_isolated_database,
    bearer,
    expired_access_for,
    make_users,
    refresh_for,
    wrong_signature_access_for,
)

NX = 999999  # an id that never exists

SA = {"super_admin"}
BOTH = {"super_admin", "store_manager"}
PUBLIC = "public"

# (path under /api/admin/, HTTP method, allowed roles)
ROUTES = [
    ("adminlogin/", "POST", PUBLIC),
    ("view_users/", "GET", SA),
    # categories
    ("add_category/", "POST", BOTH),
    ("view_categories/", "GET", BOTH),
    (f"update_category/{NX}/", "POST", BOTH),
    (f"delete_category/{NX}/", "DELETE", BOTH),
    # brands
    ("add_brand/", "POST", BOTH),
    ("view_brands/", "GET", BOTH),
    (f"update_brand/{NX}/", "PUT", BOTH),
    (f"delete_brand/{NX}/", "DELETE", BOTH),
    # products
    ("add_products/", "POST", BOTH),
    ("view_products/", "GET", BOTH),
    (f"update_product/{NX}/", "POST", BOTH),
    (f"delete_product/{NX}/", "DELETE", SA),
    (f"products/{NX}/", "GET", BOTH),
    # orders / shipments
    ("view_orders/", "GET", BOTH),
    (f"update_order/{NX}/", "POST", BOTH),
    (f"order_detail_api/{NX}", "GET", BOTH),
    (f"create_shipment/{NX}/", "POST", BOTH),
    (f"orders/{NX}/create-shipment/", "POST", BOTH),
    # coupons
    ("add_coupon/", "POST", SA),
    ("view_coupons/", "GET", BOTH),
    (f"update_coupon/{NX}/", "PUT", SA),
    (f"delete_coupon/{NX}/", "DELETE", SA),
    # webhooks (public by design; signature-verified, not role-based)
    ("stripe/webhook/", "POST", PUBLIC),
    ("payments/ziina/webhook/", "POST", PUBLIC),
    # dashboard / notifications
    ("dashboard_stats/", "GET", SA),
    ("notifications/", "GET", BOTH),
    # subcategories
    ("subcategories/create/", "POST", BOTH),
    ("subcategories/", "GET", BOTH),
    (f"subcategories/{NX}/update/", "PUT", BOTH),
    (f"subcategories/{NX}/delete/", "DELETE", BOTH),
    # frames
    ("frames/create/", "POST", BOTH),
    ("frames/", "GET", BOTH),
    (f"frames/update/{NX}/", "POST", BOTH),
    (f"frames/delete/{NX}/", "DELETE", BOTH),
    # materials
    ("materials/create/", "POST", BOTH),
    ("materials/", "GET", BOTH),
    (f"materials/update/{NX}/", "PUT", BOTH),
    (f"materials/delete/{NX}/", "DELETE", BOTH),
    # suppliers
    ("supplier_list/", "GET", BOTH),
    ("add_supplier/", "POST", SA),
    (f"supplier_detail/{NX}/", "GET", BOTH),
    (f"update_supplier/{NX}/", "PUT", SA),
    (f"delete_supplier/{NX}/", "DELETE", SA),
    # shipping partners
    ("shipping-partners/", "GET", BOTH),
    ("shipping-partners/create/", "POST", SA),
    (f"shipping-partners/{NX}/", "GET", BOTH),
    (f"shipping-partners/{NX}/update/", "PUT", SA),
    (f"shipping-partners/{NX}/delete/", "DELETE", SA),
]

ROLE_ACTORS = [
    "customer",
    "staff_plain",
    "group_not_staff",
    "store_manager",
    "super_admin",
]
BAD_TOKEN_ACTORS = [
    "no_token",
    "garbage_token",
    "expired_token",
    "wrong_signature_token",
    "refresh_token_as_access",
    "inactive_user_token",
    "no_bearer_prefix",
]


class AdminAccessBase(TestCase):
    @classmethod
    def setUpClass(cls):
        assert_isolated_database()
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.users = make_users()

    def setUp(self):
        cache.clear()
        self.client = Client(raise_request_exception=False)

    # -- helpers --------------------------------------------------------
    def auth_for(self, actor):
        u = self.users
        if actor in u and actor != "inactive_manager":
            return bearer(access_for(u[actor]))
        return {
            "no_token": {},
            "garbage_token": bearer("this.is.not-a-jwt"),
            "expired_token": bearer(expired_access_for(u["super_admin"])),
            "wrong_signature_token": bearer(
                wrong_signature_access_for(u["super_admin"])
            ),
            "refresh_token_as_access": bearer(refresh_for(u["super_admin"])),
            "inactive_user_token": bearer(access_for(u["inactive_manager"])),
            "no_bearer_prefix": {
                "HTTP_AUTHORIZATION": access_for(u["super_admin"])
            },
        }[actor]

    def call(self, actor, method, path, body=None):
        cache.clear()  # keep the login throttle out of the matrix
        extra = self.auth_for(actor)
        payload = json.dumps(body if body is not None else {})
        # each call in its own savepoint: views swallow DB errors
        with transaction.atomic():
            return getattr(self.client, method.lower())(
                f"/api/admin/{path}",
                data=payload if method != "GET" else None,
                content_type="application/json",
                **extra,
            )


class AdminRouteMatrixTests(AdminAccessBase):
    def test_every_admin_route_is_covered_by_this_matrix(self):
        """Fails when a route is added to urls.py without a matrix entry."""
        import re

        tested = set()
        for path, _, _ in ROUTES:
            tested.add(re.sub(rf"{NX}", "<id>", path))

        def walk(patterns, prefix=""):
            for p in patterns:
                if hasattr(p, "url_patterns"):
                    yield from walk(p.url_patterns, prefix + str(p.pattern))
                else:
                    yield prefix + str(p.pattern)

        declared = set()
        for route in walk(get_resolver().url_patterns):
            if route.startswith("api/admin/"):
                tail = route[len("api/admin/"):]
                declared.add(re.sub(r"<int:\w+>", "<id>", tail))
        self.assertEqual(len(ROUTES), 50)
        self.assertEqual(declared - tested, set(), "untested admin routes")
        self.assertEqual(tested - declared, set(), "stale matrix entries")

    def test_role_matrix_all_routes_get_and_write(self):
        for path, method, allowed in ROUTES:
            if allowed == PUBLIC:
                continue
            # --- credentials missing / bad -> 401 -------------------------
            for actor in BAD_TOKEN_ACTORS:
                with self.subTest(route=path, method=method, actor=actor):
                    r = self.call(actor, method, path)
                    self.assertEqual(r.status_code, 401, r.content[:200])
            # --- authenticated but wrong role -> 403; right role -> ok ----
            for actor in ROLE_ACTORS:
                with self.subTest(route=path, method=method, actor=actor):
                    r = self.call(actor, method, path)
                    if actor in allowed:
                        self.assertNotIn(
                            r.status_code, (401, 403), r.content[:200]
                        )
                    else:
                        self.assertEqual(
                            r.status_code, 403, r.content[:200]
                        )

    def test_public_routes_have_no_auth_wall(self):
        for path, method, allowed in ROUTES:
            if allowed != PUBLIC:
                continue
            with self.subTest(route=path):
                r = self.call("no_token", method, path)
                self.assertNotIn(r.status_code, (403, 404, 405))
                # login with empty credentials is a clean 401 (not a 500)
                if path == "adminlogin/":
                    self.assertEqual(r.status_code, 401)

    def test_wrong_http_method_is_not_authorised_bypass(self):
        # anonymous request with an unsupported verb must not reach the view
        r = self.call("no_token", "DELETE", "view_users/")
        self.assertIn(r.status_code, (401, 405))
        self.assertEqual(User.objects.count(), len(self.users))


class AdminWriteEffectTests(AdminAccessBase):
    """Denied writes must not change data; allowed writes must still work."""

    def test_store_manager_can_add_brand(self):
        r = self.call("store_manager", "POST", "add_brand/", {"name": "Rolex"})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(Brand.objects.filter(name="Rolex").exists())

    def test_anonymous_and_customer_cannot_add_brand(self):
        for actor in ("no_token", "customer", "staff_plain"):
            self.call(actor, "POST", "add_brand/", {"name": "Evil"})
        self.assertFalse(Brand.objects.filter(name="Evil").exists())

    def test_store_manager_cannot_create_coupon_but_super_admin_can(self):
        body = {
            "code": "SAVE10",
            "discount": "10.00",
            "expiration_date": date(2099, 1, 1).isoformat(),
        }
        r = self.call("store_manager", "POST", "add_coupon/", body)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Coupon.objects.count(), 0)

        r = self.call("super_admin", "POST", "add_coupon/", body)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Coupon.objects.count(), 1)

    def test_store_manager_can_view_coupons_but_not_modify_or_delete(self):
        c = Coupon.objects.create(
            code="KEEP", discount=5, expiration_date=date(2099, 1, 1)
        )
        r = self.call("store_manager", "GET", "view_coupons/")
        self.assertEqual(r.status_code, 200)
        r = self.call(
            "store_manager", "PUT", f"update_coupon/{c.id}/", {"discount": 90}
        )
        self.assertEqual(r.status_code, 403)
        r = self.call("store_manager", "DELETE", f"delete_coupon/{c.id}/")
        self.assertEqual(r.status_code, 403)
        c.refresh_from_db()
        self.assertEqual(int(c.discount), 5)

    def test_product_delete_is_super_admin_only(self):
        p = Product.objects.create(name="Watch", price=10)
        r = self.call("store_manager", "DELETE", f"delete_product/{p.id}/")
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Product.objects.filter(id=p.id).exists())

        r = self.call("super_admin", "DELETE", f"delete_product/{p.id}/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(Product.objects.filter(id=p.id).exists())

    def test_store_manager_can_view_products(self):
        Product.objects.create(name="Watch", price=10)
        r = self.call("store_manager", "GET", "view_products/")
        self.assertEqual(r.status_code, 200)

    def test_store_manager_can_update_order_status(self):
        o = Order.objects.create(email="a@example.test")
        r = self.call(
            "store_manager",
            "POST",
            f"update_order/{o.id}/",
            {"status": "processing"},
        )
        self.assertEqual(r.status_code, 200, r.content)
        o.refresh_from_db()
        self.assertEqual(o.status, "processing")

    def test_customer_cannot_view_or_update_orders(self):
        o = Order.objects.create(email="a@example.test")
        r = self.call("customer", "GET", "view_orders/")
        self.assertEqual(r.status_code, 403)
        r = self.call("customer", "GET", f"order_detail_api/{o.id}")
        self.assertEqual(r.status_code, 403)
        r = self.call(
            "customer", "POST", f"update_order/{o.id}/", {"status": "cancelled"}
        )
        self.assertEqual(r.status_code, 403)
        o.refresh_from_db()
        self.assertEqual(o.status, "pending")

    def test_supplier_writes_are_super_admin_only(self):
        s = Supplier.objects.create(name="ACME")
        for method, path, body in [
            ("POST", "add_supplier/", {"name": "New"}),
            ("PUT", f"update_supplier/{s.id}/", {"name": "Hacked"}),
            ("DELETE", f"delete_supplier/{s.id}/", None),
        ]:
            r = self.call("store_manager", method, path, body)
            self.assertEqual(r.status_code, 403, path)
        self.assertEqual(Supplier.objects.count(), 1)
        s.refresh_from_db()
        self.assertEqual(s.name, "ACME")
        self.assertEqual(
            self.call("store_manager", "GET", "supplier_list/").status_code,
            200,
        )
        self.assertEqual(
            self.call(
                "super_admin", "POST", "add_supplier/", {"name": "New"}
            ).status_code,
            201,
        )

    def test_shipping_partner_writes_are_super_admin_only(self):
        sp = ShippingPartner.objects.create(name="DHL")
        for method, path in [
            ("POST", "shipping-partners/create/"),
            ("PUT", f"shipping-partners/{sp.id}/update/"),
            ("DELETE", f"shipping-partners/{sp.id}/delete/"),
        ]:
            r = self.call("store_manager", method, path, {"name": "x"})
            self.assertEqual(r.status_code, 403, path)
        self.assertTrue(ShippingPartner.objects.filter(id=sp.id).exists())
        for path in ("shipping-partners/", f"shipping-partners/{sp.id}/"):
            r = self.call("store_manager", "GET", path)
            self.assertEqual(r.status_code, 200, path)

    def test_user_listing_super_admin_only_and_no_data_leak(self):
        r = self.call("store_manager", "GET", "view_users/")
        self.assertEqual(r.status_code, 403)
        self.assertNotIn(b"customer@example.test", r.content)
        r = self.call("no_token", "GET", "view_users/")
        self.assertEqual(r.status_code, 401)
        self.assertNotIn(b"customer@example.test", r.content)
        r = self.call("super_admin", "GET", "view_users/")
        self.assertEqual(r.status_code, 200)

    def test_dashboard_stats_super_admin_only(self):
        self.assertEqual(
            self.call("store_manager", "GET", "dashboard_stats/").status_code,
            403,
        )


class AdminLoginTests(AdminAccessBase):
    URL = "/api/admin/adminlogin/"

    def login(self, email, password=PASSWORD):
        cache.clear()
        return self.client.post(
            self.URL,
            data=json.dumps({"email": email, "password": password}),
            content_type="application/json",
        )

    def test_super_admin_login_and_response_shape(self):
        r = self.login("super_admin@example.test")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["role"], "super_admin")
        self.assertEqual(
            set(body),
            {"message", "user_id", "email", "full_name", "role", "tokens"},
        )
        self.assertEqual(set(body["tokens"]), {"refresh", "access"})

    def test_returned_access_token_works_on_protected_route(self):
        token = self.login("store_manager@example.test").json()["tokens"][
            "access"
        ]
        r = self.client.get(
            "/api/admin/view_brands/", **bearer(token)
        )
        self.assertEqual(r.status_code, 200)

    def test_store_manager_login_role(self):
        r = self.login("store_manager@example.test")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["role"], "store_manager")

    def test_plain_staff_and_customer_cannot_log_in_to_admin(self):
        self.assertEqual(self.login("staff_plain@example.test").status_code, 403)
        self.assertEqual(self.login("customer@example.test").status_code, 403)

    def test_bad_credentials(self):
        self.assertEqual(self.login("nobody@example.test").status_code, 401)
        self.assertEqual(
            self.login("super_admin@example.test", "wrong").status_code, 401
        )
        self.assertEqual(self.login(None).status_code, 401)

    def test_duplicate_email_does_not_crash(self):
        User.objects.create_user(
            username="dup", email="super_admin@example.test", password="x1y2z3!!"
        )
        self.assertEqual(self.login("super_admin@example.test").status_code, 200)

    def test_duplicate_email_authenticates_only_the_matching_password(self):
        # a customer registered first with the same e-mail but ANOTHER password
        User.objects.create_user(
            username="dupcust", email="super_admin@example.test",
            password="Other-Pass-123!",
        )
        r = self.login("super_admin@example.test", PASSWORD)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["user_id"], self.users["super_admin"].id)
        self.assertEqual(r.json()["role"], "super_admin")
        # the customer's password must NOT log in as the admin
        r = self.login("super_admin@example.test", "Other-Pass-123!")
        self.assertEqual(r.status_code, 403)  # authenticated as non-staff
        self.assertNotIn("tokens", r.json())

    def test_duplicate_email_same_password_prefers_staff_not_customer(self):
        User.objects.create_user(
            username="aaa_first_customer", email="super_admin@example.test",
            password=PASSWORD,
        )
        r = self.login("super_admin@example.test", PASSWORD)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["user_id"], self.users["super_admin"].id)

    def test_duplicate_staff_accounts_same_password_are_refused(self):
        User.objects.create_user(
            username="second_admin", email="super_admin@example.test",
            password=PASSWORD, is_staff=True, is_superuser=True,
        )
        r = self.login("super_admin@example.test", PASSWORD)
        self.assertEqual(r.status_code, 401)
        self.assertNotIn("tokens", r.json())
