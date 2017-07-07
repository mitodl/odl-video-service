"""
Permissions for ui app
"""
from django.contrib.auth.decorators import user_passes_test
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated,
    SAFE_METHODS
)


admin_required = user_passes_test(lambda u: u.is_staff)


class IsAdminOrReadOnly(BasePermission):
    """IsAdminOrReadOnly permission"""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsAdminOrHasMoiraPermissions(IsAuthenticated):
    """IsAdminOrHasMoiraPermissions permission"""
    def has_object_permission(self, request, view, obj):
        if request.user == obj.creator or request.user.is_superuser:
            return True
        moira_user = request.user.email
        if moira_user.endswith("@mit.edu"):
            moira_user = moira_user[:-8]
        for moira_list in obj.moira_lists.all():
            if moira_user in moira_list.members():
                return True
        return False
