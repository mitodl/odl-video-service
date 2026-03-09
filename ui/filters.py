"""
Filters for ui app
"""

import django_filters
from django.db.models import Q

from ui.models import Collection, EdxEndpoint, Video


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


class PublicVideoFilter(django_filters.FilterSet):
    """
    Filter for public video list endpoint.
    Supports filtering by video fields and collection fields.
    """

    title = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    description = django_filters.CharFilter(
        field_name="description", lookup_expr="icontains"
    )
    status = django_filters.CharFilter(field_name="status", lookup_expr="exact")
    collection = django_filters.UUIDFilter(
        field_name="collection__key", lookup_expr="exact"
    )
    collection_title = django_filters.CharFilter(
        field_name="collection__title", lookup_expr="icontains"
    )
    stream_source = django_filters.CharFilter(
        field_name="collection__stream_source", lookup_expr="iexact"
    )
    exclude_source = django_filters.CharFilter(method="exclude_source_filter")
    search = django_filters.CharFilter(method="search_filter")

    def exclude_source_filter(self, queryset, name, value):  # pylint: disable=unused-argument
        """
        Exclude videos whose collection stream_source matches the given value
        (case-insensitive). Accepts a single value or a comma-separated list
        of values to exclude multiple sources at once.
        """
        sources = [s.strip() for s in value.split(",") if s.strip()]
        for source in sources:
            queryset = queryset.exclude(collection__stream_source__iexact=source)
        return queryset

    def search_filter(self, queryset, name, value):  # pylint: disable=unused-argument
        """
        Full-text search across video title, video description,
        collection title, and collection description.
        """
        return queryset.filter(
            Q(title__icontains=value)
            | Q(description__icontains=value)
            | Q(collection__title__icontains=value)
            | Q(collection__description__icontains=value)
        ).distinct()

    class Meta:
        model = Video
        fields = [
            "title",
            "description",
            "status",
            "collection",
            "collection_title",
            "stream_source",
            "exclude_source",
        ]
