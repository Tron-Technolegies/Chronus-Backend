"""
Django's built-in /admin/ is restricted to active Super Admins only.

Run with:  python manage.py test --settings=ProjectChronas.settings_test
"""
from django.contrib.auth.models import Group, Permission, User
from django.test import Client, TestCase

from .rbac_testkit import (
    PASSWORD,
    access_for,
    assert_isolated_database,
    bearer,
    make_users,
)

PAGES = ("/admin/", "/admin/auth/user/", "/admin/auth/group/")


class DjangoAdminAccessTests(TestCase):
    @classmethod
    def setUpClass(cls):
        assert_isolated_database()
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.users = make_users()
        cls.inactive_super = User.objects.create_user(
            "inactive_super",
            email="inactive_super@example.test",
            password=PASSWORD,
            is_staff=True,
            is_superuser=True,
            is_active=False,
        )

    def session_client(self, user):
        client = Client(raise_request_exception=False)
        client.force_login(user)
        return client

    def assertDenied(self, response, url):
        # not authorised -> bounced to the admin login page, never a 200
        self.assertEqual(response.status_code, 302, url)
        self.assertIn("/admin/login/", response["Location"], url)

    # -- already-authenticated sessions ----------------------------------
    def test_active_super_admin_is_allowed(self):
        client = self.session_client(self.users["super_admin"])
        for url in PAGES:
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 200)

    def test_store_manager_is_denied(self):
        client = self.session_client(self.users["store_manager"])
        for url in PAGES:
            with self.subTest(url=url):
                self.assertDenied(client.get(url), url)

    def test_ordinary_staff_is_denied(self):
        client = self.session_client(self.users["staff_plain"])
        for url in PAGES:
            with self.subTest(url=url):
                self.assertDenied(client.get(url), url)

    def test_customer_is_denied(self):
        client = self.session_client(self.users["customer"])
        for url in PAGES:
            with self.subTest(url=url):
                self.assertDenied(client.get(url), url)

    def test_inactive_super_admin_is_denied(self):
        client = self.session_client(self.inactive_super)
        for url in PAGES:
            with self.subTest(url=url):
                self.assertDenied(client.get(url), url)

    def test_super_admin_deactivated_mid_session_is_denied(self):
        user = self.users["super_admin"]
        client = self.session_client(user)
        self.assertEqual(client.get("/admin/").status_code, 200)
        User.objects.filter(pk=user.pk).update(is_active=False)
        self.assertDenied(client.get("/admin/"), "/admin/")

    def test_anonymous_is_denied(self):
        client = Client()
        for url in PAGES:
            with self.subTest(url=url):
                self.assertDenied(client.get(url), url)

    def test_super_admin_demoted_mid_session_is_denied(self):
        user = self.users["super_admin"]
        client = self.session_client(user)
        self.assertEqual(client.get("/admin/").status_code, 200)
        User.objects.filter(pk=user.pk).update(is_superuser=False)
        self.assertDenied(client.get("/admin/"), "/admin/")

    # -- the escalation scenario this fix exists for ----------------------
    def test_manager_with_user_and_group_permissions_still_denied(self):
        group = Group.objects.get(name="Store Manager")
        group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="auth",
                content_type__model__in=["user", "group"],
            )
        )
        manager = User.objects.get(pk=self.users["store_manager"].pk)
        client = self.session_client(manager)

        for url in PAGES + (
            f"/admin/auth/user/{manager.pk}/change/",
            f"/admin/auth/user/{self.users['super_admin'].pk}/password/",
            f"/admin/auth/group/{group.pk}/change/",
        ):
            with self.subTest(url=url):
                self.assertDenied(client.get(url), url)

        # write attempts: self-promotion, super-admin password reset, and
        # adding every permission to their own group must all fail
        client.post(
            f"/admin/auth/user/{manager.pk}/change/",
            {"username": manager.username, "is_staff": "on",
             "is_superuser": "on", "is_active": "on"},
        )
        client.post(
            f"/admin/auth/user/{self.users['super_admin'].pk}/password/",
            {"password1": "Hijack-Pass-123!x", "password2": "Hijack-Pass-123!x"},
        )
        client.post(
            f"/admin/auth/group/{group.pk}/change/",
            {"name": "Store Manager",
             "permissions": list(Permission.objects.values_list("pk", flat=True))},
        )
        manager.refresh_from_db()
        self.assertFalse(manager.is_superuser)
        self.assertFalse(
            User.objects.get(pk=self.users["super_admin"].pk).check_password(
                "Hijack-Pass-123!x"
            )
        )
        self.assertEqual(
            group.permissions.count(),
            Permission.objects.filter(
                content_type__app_label="auth",
                content_type__model__in=["user", "group"],
            ).count(),
        )

    # -- the login form itself -------------------------------------------
    def login(self, user, password=PASSWORD):
        client = Client(raise_request_exception=False)
        response = client.post(
            "/admin/login/",
            {"username": user.username, "password": password, "next": "/admin/"},
        )
        return client, response

    def test_login_form_accepts_super_admin_only(self):
        client, response = self.login(self.users["super_admin"])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/")
        self.assertIn("_auth_user_id", client.session)
        self.assertEqual(client.get("/admin/").status_code, 200)

        for key in ("store_manager", "staff_plain", "customer"):
            with self.subTest(user=key):
                client, response = self.login(self.users[key])
                self.assertEqual(response.status_code, 200)  # form re-shown
                self.assertNotIn("_auth_user_id", client.session)

        client, response = self.login(self.inactive_super)
        self.assertNotIn("_auth_user_id", client.session)

    def test_wrong_password_for_super_admin_is_rejected(self):
        client, response = self.login(self.users["super_admin"], "wrong")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", client.session)


class ApiUnaffectedByDjangoAdminGateTests(TestCase):
    """The /api/admin/ JWT RBAC must behave exactly as before."""

    @classmethod
    def setUpClass(cls):
        assert_isolated_database()
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.users = make_users()

    def test_store_manager_jwt_still_works_on_api_but_not_on_django_admin(self):
        client = Client(raise_request_exception=False)
        token = bearer(access_for(self.users["store_manager"]))
        self.assertEqual(
            client.get("/api/admin/view_brands/", **token).status_code, 200
        )
        self.assertEqual(
            client.get("/api/admin/view_users/", **token).status_code, 403
        )
        self.assertEqual(client.get("/admin/", **token).status_code, 302)

    def test_super_admin_jwt_still_works_on_api(self):
        client = Client(raise_request_exception=False)
        token = bearer(access_for(self.users["super_admin"]))
        self.assertEqual(
            client.get("/api/admin/view_users/", **token).status_code, 200
        )

    def test_django_admin_session_is_not_accepted_by_the_api(self):
        client = Client(raise_request_exception=False)
        client.force_login(self.users["super_admin"])
        self.assertEqual(client.get("/admin/").status_code, 200)
        self.assertEqual(client.get("/api/admin/view_users/").status_code, 401)
