"""
Role-based access control for the Chronos admin API.

Roles are ALWAYS derived from the authenticated backend user (database),
never from anything the client sends:

    Super Admin    -> active user with is_staff and is_superuser
    Store Manager  -> active user with is_staff, in the "Store Manager" group
    Ordinary staff -> is_staff only: NO admin API access
    Customer       -> never has admin API access

Two ways to apply a permission:

* DRF views (@api_view):      @permission_classes([SuperAdminPermission])
* plain Django views:         @admin_access(SuperAdminPermission)

`admin_access` authenticates the Bearer JWT itself (plain Django views never
go through DRF's authentication pipeline) and returns 401 for a missing,
invalid or expired token and 403 for an authenticated user without the role.
It does not touch request parsing, so request.POST / request.FILES /
request.body behave exactly as before.
"""
from functools import wraps

from django.http import JsonResponse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError

STORE_MANAGER_GROUP = "Store Manager"


def _is_active_staff(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
    )


def is_super_admin(user):
    return _is_active_staff(user) and user.is_superuser


def is_store_manager(user):
    return (
        _is_active_staff(user)
        and user.groups.filter(name=STORE_MANAGER_GROUP).exists()
    )


class SuperAdminPermission(BasePermission):
    """Super Admin only."""

    def has_permission(self, request, view):
        return is_super_admin(request.user)


class StoreManagerPermission(BasePermission):
    """
    Store Manager only (staff + "Store Manager" group).

    Superusers are NOT implicitly accepted here; use
    StoreManagerOrSuperAdmin for endpoints both roles may use.
    """

    def has_permission(self, request, view):
        return is_store_manager(request.user)


class StoreManagerOrSuperAdmin(BasePermission):
    """Operational endpoints available to both admin roles."""

    def has_permission(self, request, view):
        user = request.user
        return is_super_admin(user) or is_store_manager(user)


def admin_access(permission_class):
    """
    Decorator for plain Django views: JWT-authenticate, then authorise.

    401 -> no / malformed / invalid / expired token, unknown or inactive user
    403 -> valid token but the user lacks the required role
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            try:
                result = JWTAuthentication().authenticate(request)
            except (AuthenticationFailed, TokenError):
                return _unauthorized("Invalid or expired token.")

            if result is None:
                return _unauthorized(
                    "Authentication credentials were not provided."
                )

            request.user, request.auth = result

            if not permission_class().has_permission(request, None):
                return JsonResponse(
                    {
                        "detail": (
                            "You do not have permission to perform "
                            "this action."
                        )
                    },
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        # introspection hook: lets tests assert the declared permission of
        # every route (functools.wraps in outer decorators preserves it)
        wrapped.rbac_permission = permission_class
        return wrapped

    return decorator


def _unauthorized(message):
    response = JsonResponse({"detail": message}, status=401)
    response["WWW-Authenticate"] = 'Bearer realm="api"'
    return response
