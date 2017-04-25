from django.contrib.auth.decorators import user_passes_test
from rest_framework.permissions import BasePermission, SAFE_METHODS


admin_required = user_passes_test(lambda u: u.is_staff)


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        else:
            return request.user.is_staff
