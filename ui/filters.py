"""
Filters for ui app
"""

import django_filters
from django.db.models import Q

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
        Search filter that looks across title, description and edx_course_id
        """
        return queryset.filter(
            Q(title__icontains=value)
            | Q(description__icontains=value)
            | Q(edx_course_id__icontains=value)
            | Q(slug__icontains=value)
        )

    class Meta:
        model = Collection
        fields = ["title", "slug", "description", "edx_course_id", "edx_endpoint"]
