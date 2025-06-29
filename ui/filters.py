"""
Filters for ui app
"""

import django_filters
from django.db.models import Q
from django.contrib.auth import get_user_model

from ui.models import Collection, EdxEndpoint


class CollectionFilter(django_filters.FilterSet):
    """
    Filter for Collection model
    """

    title = django_filters.CharFilter(lookup_expr="icontains")
    slug = django_filters.CharFilter(lookup_expr="icontains")
    description = django_filters.CharFilter(lookup_expr="icontains")
    edx_course_id = django_filters.CharFilter(lookup_expr="icontains")
    edx_endpoint = django_filters.ModelChoiceFilter(
        queryset=EdxEndpoint.objects.all(),
        field_name="edx_endpoints",
    )
    search = django_filters.CharFilter(method="search_filter")

    def search_filter(self, queryset, name, value):  # pylint: disable=unused-argument
        """
        Search filter that looks across collection fields (title, description, edx_course_id, slug)
        and video fields (title, description)
        """
        return queryset.filter(
            Q(title__icontains=value)
            | Q(description__icontains=value)
            | Q(edx_course_id__icontains=value)
            | Q(slug__icontains=value)
            | Q(videos__title__icontains=value)
            | Q(videos__description__icontains=value)
        ).distinct()

    class Meta:
        model = Collection
        fields = ["title", "slug", "description", "edx_course_id", "edx_endpoint"]


class UserFilter(django_filters.FilterSet):
    """
    Filter for User model
    """

    username = django_filters.CharFilter(lookup_expr="icontains")
    email = django_filters.CharFilter(lookup_expr="icontains")
    first_name = django_filters.CharFilter(lookup_expr="icontains")
    last_name = django_filters.CharFilter(lookup_expr="icontains")
    search = django_filters.CharFilter(method="search_filter")

    def search_filter(self, queryset, name, value):  # pylint: disable=unused-argument
        """
        Search filter that looks across user fields (username, email, first_name, last_name)
        """
        return queryset.filter(
            Q(username__icontains=value)
            | Q(email__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
        ).distinct()

    class Meta:
        model = get_user_model()
        fields = ["username", "email", "first_name", "last_name"]
