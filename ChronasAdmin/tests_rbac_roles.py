"""
RBAC-focused tests: declared permissions, token formats, role definitions and
the admin_access decorator itself.

Run with:  python manage.py test --settings=ProjectChronas.settings_test
"""
import json

from django.contrib.auth.models import AnonymousUser, Group, User
from django.core.cache import cache
from django.http import JsonResponse
from django.test import RequestFactory, TestCase
from django.urls import resolve

from ChronasAdmin.models import Brand

from . import tests_permissions as tp
from .permissions import (
    StoreManagerOrSuperAdmin,
    SuperAdminPermission,
    admin_access,
)
from .rbac_testkit import (
    PASSWORD,
    access_for,
    assert_isolated_database,
    bearer,
    make_users,
)


class DeclaredPermissionTests(tp.AdminAccessBase):
    """Structural check: each route DECLARES the agreed permission class and
    it is really enforced. A plain Django view carrying only a stray
    @permission_classes attribute has no `rbac_permission`, so it fails."""

    def test_every_protected_route_declares_the_agreed_permission(self):
        expected = {
            frozenset(tp.SA): SuperAdminPermission,
            frozenset(tp.BOTH): StoreManagerOrSuperAdmin,
        }
        checked = 0
        for path, method, allowed in tp.ROUTES:
            if allowed == tp.PUBLIC:
                continue
            checked += 1
            with self.subTest(route=path):
                callback = resolve(f"/api/admin/{path}").func
                want = expected[frozenset(allowed)]
                if hasattr(callback, "cls"):  # DRF @api_view
                    self.assertEqual(
                        list(callback.cls.permission_classes), [want]
                    )
                else:  # plain Django view wrapped by @admin_access
                    self.assertIs(
                        getattr(callback, "rbac_permission", None), want
                    )
        self.assertEqual(checked, 47)

    def test_public_admin_routes_are_exactly_login_and_two_webhooks(self):
        public = sorted(p for p, _, a in tp.ROUTES if a == tp.PUBLIC)
        self.assertEqual(
            public,
            ["adminlogin/", "payments/ziina/webhook/", "stripe/webhook/"],
        )

    def test_alternate_urls_for_same_function_share_protection(self):
        a = resolve(f"/api/admin/create_shipment/{tp.NX}/").func
        b = resolve(f"/api/admin/orders/{tp.NX}/create-shipment/").func
        self.assertIs(a.rbac_permission, b.rbac_permission)
        self.assertIs(a.rbac_permission, StoreManagerOrSuperAdmin)


class TokenFormatTests(tp.AdminAccessBase):
    """Missing / malformed / invalid credentials are always 401."""

    PLAIN_VIEW = "view_brands/"      # protected by @admin_access
    DRF_VIEW = "notifications/"      # @api_view + permission_classes

    def header_variants(self):
        good = access_for(self.users["super_admin"])
        return {
            "empty header": "",
            "Bearer without token": "Bearer",
            "Bearer and a space only": "Bearer ",
            "two tokens": f"Bearer {good} {good}",
            "token + trailing junk": f"Bearer {good} extra",
            "lowercase scheme": f"bearer {good}",
            "wrong scheme (Token)": f"Token {good}",
            "wrong scheme (Basic)": f"Basic {good}",
            "bare token no scheme": good,
            "garbled token": f"Bearer {good[:-5]}xxxxx",
            "three dots": "Bearer a.b.c",
        }

    def test_malformed_authorization_headers_return_401(self):
        for view in (self.PLAIN_VIEW, self.DRF_VIEW):
            for label, value in self.header_variants().items():
                with self.subTest(view=view, header=label):
                    cache.clear()
                    r = self.client.get(
                        f"/api/admin/{view}", HTTP_AUTHORIZATION=value
                    )
                    self.assertEqual(r.status_code, 401, r.content[:150])

    def test_401_carries_www_authenticate_header(self):
        r = self.client.get(f"/api/admin/{self.PLAIN_VIEW}")
        self.assertEqual(r.status_code, 401)
        self.assertIn("Bearer", r["WWW-Authenticate"])

    def test_token_for_deleted_user_is_401(self):
        token = access_for(self.users["super_admin"])
        User.objects.filter(pk=self.users["super_admin"].pk).delete()
        r = self.client.get(f"/api/admin/{self.PLAIN_VIEW}", **bearer(token))
        self.assertEqual(r.status_code, 401)

    def test_401_and_403_bodies_leak_nothing(self):
        for actor, status in (("no_token", 401), ("customer", 403)):
            r = self.call(actor, "GET", "view_users/")
            self.assertEqual(r.status_code, status)
            self.assertEqual(list(r.json()), ["detail"])


class RoleDefinitionTests(tp.AdminAccessBase):
    """Role rules exactly as agreed - nothing broader."""

    def status(self, user, path="view_brands/"):
        cache.clear()
        return self.client.get(
            f"/api/admin/{path}", **bearer(access_for(user))
        ).status_code

    def test_super_admin_is_active_staff_superuser(self):
        self.assertEqual(
            self.status(self.users["super_admin"], "view_users/"), 200
        )

    def test_inactive_super_admin_is_denied(self):
        u = self.users["super_admin"]
        token = access_for(u)
        User.objects.filter(pk=u.pk).update(is_active=False)
        r = self.client.get("/api/admin/view_users/", **bearer(token))
        self.assertEqual(r.status_code, 401)

    def test_superuser_without_staff_flag_is_denied(self):
        u = User.objects.create_user(
            "su_nostaff", password=PASSWORD, is_superuser=True, is_staff=False
        )
        self.assertEqual(self.status(u, "view_users/"), 403)
        self.assertEqual(self.status(u, "view_brands/"), 403)

    def test_store_manager_requires_staff_and_exact_group_name(self):
        self.assertEqual(self.status(self.users["group_not_staff"]), 403)
        self.assertEqual(self.status(self.users["staff_plain"]), 403)
        for name in ("store manager", "Store Managers", "StoreManager", "Manager"):
            u = User.objects.create_user(
                "u_" + name.replace(" ", "_"), password=PASSWORD, is_staff=True
            )
            u.groups.add(Group.objects.create(name=name))
            with self.subTest(group=name):
                self.assertEqual(self.status(u), 403)
        self.assertEqual(self.status(self.users["store_manager"]), 200)

    def test_inactive_store_manager_is_denied(self):
        r = self.call("inactive_user_token", "GET", "view_brands/")
        self.assertEqual(r.status_code, 401)

    def test_store_manager_is_never_super_admin(self):
        sm = self.users["store_manager"]
        self.assertFalse(sm.is_superuser)
        self.assertEqual(self.status(sm, "view_users/"), 403)
        self.assertEqual(self.status(sm, "dashboard_stats/"), 403)
        self.assertEqual(self.status(sm, "supplier_list/"), 200)

    def test_role_changes_apply_immediately_to_existing_tokens(self):
        sm = self.users["store_manager"]
        token = access_for(sm)
        ok = self.client.get("/api/admin/view_brands/", **bearer(token))
        self.assertEqual(ok.status_code, 200)
        sm.groups.clear()  # role revoked in the database
        denied = self.client.get("/api/admin/view_brands/", **bearer(token))
        self.assertEqual(denied.status_code, 403)

    def test_role_comes_from_database_not_client_input(self):
        customer = bearer(access_for(self.users["customer"]))
        r = self.client.get(
            "/api/admin/view_users/?role=super_admin&is_superuser=true",
            HTTP_X_ROLE="super_admin",
            **customer,
        )
        self.assertEqual(r.status_code, 403)
        r = self.client.post(
            "/api/admin/add_brand/",
            data=json.dumps({"name": "X", "role": "store_manager"}),
            content_type="application/json",
            **customer,
        )
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Brand.objects.filter(name="X").exists())

    def test_superuser_also_in_group_is_still_super_admin(self):
        su = self.users["super_admin"]
        su.groups.add(Group.objects.get(name="Store Manager"))
        self.assertEqual(self.status(su, "view_users/"), 200)


class AdminAccessDecoratorTests(TestCase):
    """admin_access sets request.user and leaves the request intact."""

    @classmethod
    def setUpClass(cls):
        assert_isolated_database()
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.users = make_users()

    def test_request_user_is_set_from_jwt_and_replaces_anonymous(self):
        @admin_access(StoreManagerOrSuperAdmin)
        def probe(request):
            return JsonResponse(
                {
                    "uid": request.user.id,
                    "has_auth": request.auth is not None,
                    "body": request.body.decode(),
                    "post": request.POST.get("k"),
                }
            )

        sm = self.users["store_manager"]
        request = RequestFactory().post(
            "/probe", data={"k": "v"}, **bearer(access_for(sm))
        )
        request.user = AnonymousUser()  # what Django's middleware provides
        response = probe(request)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["uid"], sm.id)
        self.assertTrue(data["has_auth"])
        self.assertEqual(data["post"], "v")   # form parsing untouched
        self.assertIn('name="k"', data["body"])  # request.body untouched

    def test_denied_request_never_reaches_the_view(self):
        called = []

        @admin_access(SuperAdminPermission)
        def probe(request):
            called.append(1)
            return JsonResponse({})

        for user in (self.users["store_manager"], self.users["customer"]):
            request = RequestFactory().get("/probe", **bearer(access_for(user)))
            self.assertEqual(probe(request).status_code, 403)
        self.assertEqual(probe(RequestFactory().get("/probe")).status_code, 401)
        self.assertEqual(called, [])
