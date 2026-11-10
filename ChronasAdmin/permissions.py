from rest_framework.permissions import BasePermission


class StoreManagerPermission(BasePermission):

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Super Admin can access everything
        if user.is_superuser:
            return True

        # Store Manager must be staff and belong to the group
        return (
            user.is_staff
            and user.groups.filter(
                name="Store Manager"
            ).exists()
        )