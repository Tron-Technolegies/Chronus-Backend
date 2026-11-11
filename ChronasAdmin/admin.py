from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError

from .permissions import is_super_admin

# Register your models here.


# ---------------------------------------------------------------------------
# Django's built-in /admin/ is restricted to active Super Admins ONLY.
#
# Store Managers (and ordinary staff) have is_staff=True, which is Django
# Admin's default entry requirement, so without this gate they could open
# /admin/ and - if their group ever receives user/group model permissions -
# escalate privileges. This does not affect the JWT-protected /api/admin/
# endpoints, which have their own permission classes (ChronasAdmin.permissions).
# ---------------------------------------------------------------------------
class SuperAdminAuthenticationForm(AdminAuthenticationForm):
    """Admin login form that also refuses anyone who is not a Super Admin."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not is_super_admin(user):
            raise ValidationError(
                self.error_messages["invalid_login"],
                code="invalid_login",
                params={"username": self.username_field.verbose_name},
            )


def _super_admin_only(request):
    return is_super_admin(request.user)


admin.site.has_permission = _super_admin_only
admin.site.login_form = SuperAdminAuthenticationForm
