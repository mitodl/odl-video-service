"""
Permissions for ui app
"""
import logging
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
from ui.utils import user_moira_lists

log = logging.getLogger(__name__)

User = get_user_model()

admin_required = user_passes_test(lambda u: u.is_staff)


def has_common_lists(user, list_names):
    """
    Return true if the user's moira lists overlap with the collection's
    """
    return len(set(user_moira_lists(user)).intersection(list_names)) > 0


def has_view_permission(obj, request):
    """
    Determine if a user can view a collection or its videos based
    on moira lists and superuser status

    Args:
        obj (ui.models.Collection): The collection to check permission for
        request (HTTPRequest): The request object

    Returns:
        True or False

    """
    if request.user == obj.owner or request.user.is_superuser:
        return True
    if request.method in SAFE_METHODS:
        lists = list(obj.view_lists.values_list('name', flat=True)) + \
                list(obj.admin_lists.values_list('name', flat=True))
        if lists and has_common_lists(request.user, lists):
            return True
        return False
    return has_admin_permission(obj, request)


def has_admin_permission(obj, request):
    """
    Determine if a user can edit a collection or its videos based
    on moira lists and superuser status

    Args:
        obj (ui.models.Collection): The collection to check permission for
        request (HTTPRequest): The request object

    Returns:
        True or False

    """
    if request.user == obj.owner or request.user.is_superuser:
        return True
    lists = list(obj.admin_lists.values_list('name', flat=True))
    if lists and has_common_lists(request.user, lists):
        return True
    return False


class IsAdminOrReadOnly(BasePermission):
    """IsAdminOrReadOnly permission"""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_superuser


class HasCollectionPermissions(IsAuthenticated):
    """
    Permission to view or edit collection, currently both limited to users with admin access
    """
    def has_object_permission(self, request, view, obj):
        return has_admin_permission(obj, request)


class HasViewPermissionsForVideo(IsAuthenticated):
    """Permission to view a video, based on its collection"""
    def has_object_permission(self, request, view, obj):
        return has_view_permission(obj.collection, request)


class HasAdminPermissionsForVideo(IsAuthenticated):
    """Permission to edit a video, based on its collection"""
    def has_object_permission(self, request, view, obj):
        return has_admin_permission(obj.collection, request)


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
        if request.user.is_superuser:
            return True
        collection_key = request.data.get('collection')
        if collection_key is None:
            return False
        try:
            uuid.UUID(collection_key)
        except ValueError:
            raise ValidationError('wrong UUID format for {}'.format(collection_key))
        collection = Collection.objects.filter(key=collection_key)
        return len(collection) > 0 and has_admin_permission(collection.first(), request)
