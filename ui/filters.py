"""
Filters for ui app
"""

import django_filters
from django.db.models import Case, F, Func, Q, TextField, Value, When
from django.db.models.functions import Replace, Trim

from ui.constants import DescriptionFormat
from ui.models import Collection, EdxEndpoint, Video

# The entities `ui.html.plaintext_to_html` introduces and `nh3` leaves behind.
# Decoded so that a description reading "Q&A after" is still found by searching
# for "Q&A" once it is stored as "Q&amp;A after".
#
# `&amp;` goes last: decoding it first would turn a literal "&amp;lt;" into
# "&lt;" and then into "<", which is not what the author wrote.
_ENTITY_DECODES = (
    ("&lt;", "<"),
    ("&gt;", ">"),
    ("&quot;", '"'),
    ("&#39;", "'"),
    ("&nbsp;", " "),
    ("&amp;", "&"),
)


def _regexp_replace(expression, pattern, replacement):
    """
    A global `regexp_replace`, which Django has no builtin for.

    Postgres-only, and deliberately: this app runs on Postgres in development,
    in CI and in production. SQLite has no equivalent function at all, so there
    is nothing portable to fall back to.

    Args:
        expression (Expression): the value to rewrite
        pattern (str): a Postgres regular expression
        replacement (str): what each match becomes

    Returns:
        Func: the rewritten value
    """
    return Func(
        expression,
        Value(pattern),
        Value(replacement),
        Value("g"),
        function="regexp_replace",
        output_field=TextField(),
    )


def searchable_description(field_path, format_path):
    """
    A description as its reader sees it, for matching against.

    Rich-text descriptions are stored as markup in the same column plain text
    used to live in, so an `icontains` over the raw column matches the tags as
    well as the words: `?search=p` hits every description with a paragraph in
    it, and `?search=strong` every bolded one. Those are matches on encoding,
    not on content, and no one searching for them means them.

    Only an HTML-formatted row is stripped. Doing it unconditionally would
    delete text from the plain-text rows this column is still mostly full of -
    a description reading "Use <enter> to submit" would lose the "<enter>" and
    stop being findable by it.

    Expressed in SQL rather than in Python so it stays a queryset filter; used
    through `QuerySet.alias()` so it does not join the SELECT list, where it
    would give the `.distinct()` in `search_filter` a per-row value to
    distinguish collections by and stop it deduplicating them.

    Args:
        field_path (str): query path to the description column
        format_path (str): query path to that row's `description_format`

    Returns:
        Case: the description with markup removed where it is markup
    """
    # Block boundaries separate words, but inline formatting can split a word:
    # `micro<strong>biology</strong>` must still match "microbiology".
    # These are the block/line-break tags in the sanitized description vocabulary.
    text = _regexp_replace(
        F(field_path), r"</?(?:p|br|blockquote|ul|ol|li)(?:\s[^>]*)?/?>", " "
    )
    text = _regexp_replace(text, r"<[^>]*>", "")

    # After the tags, never before: decoding first would turn an escaped
    # "&lt;b&gt;" into a real tag and then strip the word between the two.
    for entity, char in _ENTITY_DECODES:
        text = Replace(text, Value(entity), Value(char))

    # Last, so it also catches the spaces the tags and `&nbsp;` just left.
    text = Trim(_regexp_replace(text, r"\s+", " "))

    return Case(
        When(**{format_path: DescriptionFormat.HTML}, then=text),
        default=F(field_path),
        output_field=TextField(),
    )


class CollectionFilter(django_filters.FilterSet):
    """
    Filter for Collection model
    """

    title = django_filters.CharFilter(lookup_expr="icontains")
    slug = django_filters.CharFilter(lookup_expr="icontains")
    description = django_filters.CharFilter(method="description_filter")
    edx_course_id = django_filters.CharFilter(lookup_expr="icontains")
    edx_endpoint = django_filters.ModelChoiceFilter(
        queryset=EdxEndpoint.objects.all(),
        field_name="edx_endpoints",
    )
    search = django_filters.CharFilter(method="search_filter")

    def description_filter(self, queryset, name, value):  # pylint: disable=unused-argument
        """
        Match a collection description by what it says, not how it is encoded.

        See `searchable_description`.
        """
        return queryset.alias(
            searchable_description=searchable_description(
                "description", "description_format"
            )
        ).filter(searchable_description__icontains=value)

    def search_filter(self, queryset, name, value):  # pylint: disable=unused-argument
        """
        Search filter that looks across collection fields (title, description, edx_course_id, slug)
        and video fields (title, description)

        Descriptions are matched on their text rather than their markup; see
        `searchable_description`.
        """
        return (
            queryset.alias(
                searchable_description=searchable_description(
                    "description", "description_format"
                ),
                searchable_video_description=searchable_description(
                    "videos__description", "videos__description_format"
                ),
                searchable_video_title=F("videos__title"),
            )
            .filter(
                Q(title__icontains=value)
                | Q(searchable_description__icontains=value)
                | Q(edx_course_id__icontains=value)
                | Q(slug__icontains=value)
                | Q(searchable_video_title__icontains=value)
                | Q(searchable_video_description__icontains=value)
            )
            .distinct()
        )

    class Meta:
        model = Collection
        fields = ["title", "slug", "description", "edx_course_id", "edx_endpoint"]


class PublicVideoFilter(django_filters.FilterSet):
    """
    Filter for public video list endpoint.
    Supports filtering by video fields and collection fields.
    """

    title = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    description = django_filters.CharFilter(method="description_filter")
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
    include_in_learn = django_filters.BooleanFilter(
        field_name="collection__include_in_learn"
    )
    for_shorts = django_filters.BooleanFilter(field_name="collection__for_shorts")
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

    def description_filter(self, queryset, name, value):  # pylint: disable=unused-argument
        """
        Match a video description by what it says, not how it is encoded.

        See `searchable_description`.
        """
        return queryset.alias(
            searchable_description=searchable_description(
                "description", "description_format"
            )
        ).filter(searchable_description__icontains=value)

    def search_filter(self, queryset, name, value):  # pylint: disable=unused-argument
        """
        Full-text search across video title, video description,
        collection title, and collection description.

        Descriptions are matched on their text rather than their markup; see
        `searchable_description`.
        """
        return (
            queryset.alias(
                searchable_description=searchable_description(
                    "description", "description_format"
                ),
                searchable_collection_description=searchable_description(
                    "collection__description", "collection__description_format"
                ),
            )
            .filter(
                Q(title__icontains=value)
                | Q(searchable_description__icontains=value)
                | Q(collection__title__icontains=value)
                | Q(searchable_collection_description__icontains=value)
            )
            .distinct()
        )

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
            "include_in_learn",
            "for_shorts",
        ]
