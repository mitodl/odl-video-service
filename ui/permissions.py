"""
Permissions for ui app
"""

import uuid

from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission

from odl_video import logging
from ui.models import Collection
from ui.utils import has_common_lists

log = logging.getLogger(__name__)

User = get_user_model()


def is_staff_or_superuser(user):
    """
    Determine if a user is either a staff or super user

    Args:
        user (django.contrib.auth.models.User): A user

    Returns:
        bool: True if user is a superuser or staff
    """
    return user.is_superuser or user.is_staff


def has_video_view_permission(obj, request):
    """
    Determine if a user can view a video

    Args:
        obj (ui.models.Video): The video to check permission for
        request (HTTPRequest): The request object

    Returns:
        bool: True if the user can view the video, False otherwise

    """
    if (
        obj.is_public
        or request.user.is_superuser
        or request.user == obj.collection.owner
    ):
        return True
    if obj.is_private:
        return has_admin_permission(obj.collection, request)
    if has_admin_permission(obj.collection, request):
        return True
    if request.method in SAFE_METHODS:
        if obj.is_logged_in_only or obj.collection.is_logged_in_only:
            return request.user.is_authenticated
        view_list = list(obj.view_lists.values_list("name", flat=True))
        if view_list:
            all_lists = view_list + list(obj.admin_lists.values_list("name", flat=True))
            return has_common_lists(request.user, all_lists)
        # check collection's view list
        return has_common_lists(
            request.user, list(obj.collection.view_lists.values_list("name", flat=True))
        )
    return False


def has_admin_permission(obj, request):
    """
    Determine if a user can edit a collection or its videos based
    on moira lists and superuser status

    Args:
        obj (ui.models.Collection): The collection to check permission for
        request (HTTPRequest): The request object

    Returns:
        bool: True if the user is a superuser or owner, or is on the admin moira list
    """
    if request.user == obj.owner or request.user.is_superuser:
        return True
    return has_common_lists(
        request.user, list(obj.admin_lists.values_list("name", flat=True))
    )


class HasCollectionPermissions(BasePermission):
    """
    Permission to view, edit, or create collections
    View/edit currently both limited to users with admin access
    Creation currently limited to staff or superusers
    """

    def has_permission(self, request, view):
        if request.method == "POST":
            if not is_staff_or_superuser(request.user):
                return False
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return has_admin_permission(obj, request)


class HasVideoPermissions(BasePermission):
    """Permission to view a video, based on its collection"""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return has_video_view_permission(obj, request)
        return has_admin_permission(obj.collection, request)


class HasVideoSubtitlePermissions(BasePermission):
    """Permission to view/edit a video videoSubtitle"""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return has_video_view_permission(obj.video, request)
        return has_admin_permission(obj.video.collection, request)


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
        collection_key = request.data.get("collection")
        if collection_key is None:
            return False
        try:
            uuid.UUID(collection_key)
        except ValueError as exc:
            raise ValidationError(
                "wrong UUID format for {}".format(collection_key)
            ) from exc
        collection = Collection.objects.filter(key=collection_key)
        return len(collection) > 0 and has_admin_permission(collection.first(), request)
