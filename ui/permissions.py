"""
Permissions for ui app
"""
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated,
    SAFE_METHODS
)

from ui.models import Collection


User = get_user_model()


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


class IsCollectionOwner(BasePermission):
    """
    Permission to check if user is owner of the collection
    """
    def has_object_permission(self, request, view, obj):
        if request.user == obj.owner or request.user.is_superuser:
            return True
        # this should check for moira lists as well
        return False


class CanUploadToCollection(BasePermission):
    """
    Permission that checks for a collection in the request.data and verifies that the user can post to it
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS or request.user.is_superuser:
            return True
        collection_key = request.data.get('collection')
        if collection_key is None:
            return False
        try:
            uuid.UUID(collection_key)
        except ValueError:
            raise ValidationError('wrong UUID format for {}'.format(collection_key))
        return Collection.objects.filter(owner=request.user, key=collection_key).exists()
