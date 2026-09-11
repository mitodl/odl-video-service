"""
Tests for ui filters
"""

import pytest
from django.db import connection

from ui.constants import DescriptionFormat
from ui.factories import CollectionFactory, VideoFactory
from ui.filters import CollectionFilter, PublicVideoFilter
from ui.models import Collection, Video

# `searchable_description` compiles to Postgres `regexp_replace`, which SQLite
# has no equivalent for. Postgres is what runs in development, in CI (see
# .github/workflows/ci.yml) and in production; a local run with no DATABASE_URL
# falls back to SQLite and skips these.
pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason="searchable_description needs Postgres regexp_replace",
    ),
]


def make_collection(description, description_format=DescriptionFormat.HTML, **kwargs):
    """
    A collection whose only searchable text is the description under test.

    The factory defaults are random - a `FuzzyText` title and a paragraph of
    Faker prose - so leaving them in place would let a one-letter search like
    `?search=p` match by luck.
    """
    return CollectionFactory.create(
        description=description,
        description_format=description_format,
        title=kwargs.pop("title", "Zzz"),
        edx_course_id=kwargs.pop("edx_course_id", ""),
        **kwargs,
    )


def make_video(description, description_format=DescriptionFormat.HTML, **kwargs):
    """A video whose only searchable text is the description under test"""
    return VideoFactory.create(
        description=description,
        description_format=description_format,
        title=kwargs.pop("title", "Zzz"),
        collection=kwargs.pop("collection", None) or make_collection(""),
        **kwargs,
    )


def matches_collection(collection, **data):
    """
    Whether CollectionFilter matches this one collection.

    Scoped to its own row rather than run over the whole table, so an unrelated
    fixture cannot decide the result.
    """
    queryset = Collection.objects.filter(pk=collection.pk)
    return list(CollectionFilter(data, queryset=queryset).qs) == [collection]


def matches_video(video, **data):
    """Whether PublicVideoFilter matches this one video"""
    queryset = Video.objects.filter(pk=video.pk)
    return list(PublicVideoFilter(data, queryset=queryset).qs) == [video]


def test_collection_search_ignores_the_markup_of_a_rich_text_description():
    """
    `?search=p` used to match every rich-text description, because the tags live
    in the same column as the words. Searching for a tag name is a search for
    encoding, not for content.
    """
    # No letter "p" and no "strong" anywhere in the *text*, so a match on
    # either can only have come from the markup.
    collection = make_collection("<p>Lectures on <strong>heat</strong></p>")

    assert matches_collection(collection, search="heat")
    assert not matches_collection(collection, search="p")
    assert not matches_collection(collection, search="strong")


def test_collection_search_still_matches_a_plain_text_description_verbatim():
    """
    Plain text is the format nearly every stored row is still in, and stripping
    tags from it would delete real words - "<enter>" is text, not a tag.
    """
    collection = make_collection(
        "Use <enter> to submit", description_format=DescriptionFormat.TEXT
    )

    assert matches_collection(collection, search="enter")


def test_collection_search_matches_text_across_an_html_entity():
    """
    A rich-text description storing "Q&amp;A" reads as "Q&A", so that is what a
    search for it has to match.
    """
    collection = make_collection("<p>Q&amp;A after the lecture</p>")

    assert matches_collection(collection, search="Q&A after")


def test_collection_search_does_not_weld_words_across_a_tag():
    """
    Two paragraphs have no whitespace between them in the markup, so removing
    the tags outright would turn "alpha" and "beta" into one word "alphabeta"
    and stop either from being found as itself.
    """
    collection = make_collection("<p>alpha</p><p>beta</p>")

    assert matches_collection(collection, search="alpha beta")
    assert not matches_collection(collection, search="alphabeta")


def test_collection_search_keeps_a_phrase_that_spans_a_tag():
    """
    The spaces left where the tags were are collapsed, so a phrase the author
    wrote with one space in it is still matched by one space.
    """
    collection = make_collection("<p>Lectures on <strong>heat</strong> today</p>")

    assert matches_collection(collection, search="Lectures on heat today")


@pytest.mark.parametrize(
    "tag", ["strong", "em", "b", "i", "u", 'a href="https://mit.edu"']
)
@pytest.mark.parametrize("field", ["search", "description"])
def test_description_filters_preserve_words_across_inline_tags(tag, field):
    """Formatting only part of a word must not make that word unsearchable."""
    closing_tag = tag.split()[0]
    description = f"<p>micro<{tag}>biology</{closing_tag}></p>"
    collection = make_collection(description)
    video = make_video(description)

    assert matches_collection(collection, **{field: "microbiology"})
    assert matches_video(video, **{field: "microbiology"})
    assert not matches_collection(collection, **{field: "micro biology"})
    assert not matches_video(video, **{field: "micro biology"})


@pytest.mark.parametrize(
    "description",
    [
        "<p>alpha</p><p>beta</p>",
        "<p>alpha<br>beta</p>",
        "<blockquote>alpha</blockquote><p>beta</p>",
        "<ul><li>alpha</li><li>beta</li></ul>",
        "<ol><li>alpha</li><li>beta</li></ol>",
    ],
)
def test_description_filters_keep_block_boundaries(description):
    """Paragraphs, line breaks and list items continue to separate words."""
    collection = make_collection(description)
    video = make_video(description)

    assert matches_collection(collection, search="alpha beta")
    assert matches_video(video, search="alpha beta")
    assert not matches_collection(collection, search="alphabeta")
    assert not matches_video(video, search="alphabeta")


def test_collection_search_returns_each_collection_once():
    """
    The video join multiplies rows, and the description expression must stay out
    of the SELECT list - in it, `.distinct()` would have a per-row value to tell
    those rows apart by and would stop deduplicating the collection.
    """
    collection = make_collection("", title="Optics")
    VideoFactory.create_batch(3, collection=collection, title="Optics lecture")

    queryset = Collection.objects.filter(pk=collection.pk)
    assert list(CollectionFilter({"search": "Optics"}, queryset=queryset).qs) == [
        collection
    ]


def test_collection_search_finds_a_videos_rich_text_description():
    """A collection is a match when one of its videos' descriptions is"""
    collection = make_collection("")
    make_video("<p>On <em>trusses</em></p>", collection=collection)

    assert matches_collection(collection, search="trusses")
    assert not matches_collection(collection, search="em")


def test_collection_description_filter_ignores_markup():
    """The documented `?description=` filter matches text, like search does"""
    collection = make_collection("<p>Lectures on <strong>heat</strong></p>")

    assert matches_collection(collection, description="heat")
    assert not matches_collection(collection, description="strong")


def test_video_search_ignores_the_markup_of_a_rich_text_description():
    """Video descriptions get the same treatment as collection descriptions"""
    video = make_video("<p>On <em>damping</em></p>")

    assert matches_video(video, search="damping")
    assert not matches_video(video, search="em")


def test_video_search_finds_its_collections_rich_text_description():
    """A video is a match when its collection's description is"""
    collection = make_collection("<p>A course on <strong>resonance</strong></p>")
    video = make_video("", collection=collection)

    assert matches_video(video, search="resonance")
    assert not matches_video(video, search="strong")


def test_video_description_filter_ignores_markup():
    """The documented `?description=` filter matches text, like search does"""
    video = make_video("<p>On <em>damping</em></p>")

    assert matches_video(video, description="damping")
    assert not matches_video(video, description="em")


def test_collection_search_joins_the_video_table_only_once():
    """
    Every video condition has to go through the same join.

    A second join on a reverse FK multiplies each collection's videos by
    themselves before DISTINCT removes them again: a 836-video collection alone
    becomes ~700k rows, and modelling the top 50 production collections turned a
    0.03s query into 47s - past the request timeout, so search would simply stop
    working.

    Django reuses one join for conditions in a single `filter()`, but `alias()`
    opens its own, so a `videos__*` lookup left in the `filter()` alongside an
    aliased `videos__*` expression is a second join. Keeping the plain title
    lookup out of the `filter()` is what holds this to one.
    """
    sql = str(
        CollectionFilter(
            {"search": "anything"}, queryset=Collection.objects.all()
        ).qs.query
    )

    assert sql.count('JOIN "ui_video"') == 1


def test_video_search_joins_the_collection_table_only_once():
    """
    The same guarantee for the video filter.

    `collection` is a forward FK rather than a reverse one, so there is no fan-out
    to multiply here - but the join count is still the thing that would regress
    if a `collection__*` lookup were added back into the `filter()`.
    """
    sql = str(
        PublicVideoFilter({"search": "anything"}, queryset=Video.objects.all()).qs.query
    )

    assert sql.count('JOIN "ui_collection"') == 1


def test_collection_search_matches_a_video_by_title_or_description():
    """
    One join must not turn the OR into an AND.

    Routing the title through the same join is only safe because these are
    disjunctions: a collection matches when *some* video matches *either*
    condition, which is the same set either way. A collection whose title match
    and description match live on different videos still has to be found.
    """
    collection = make_collection("", title="Zzz")
    make_video("", title="Lecture on turbines", collection=collection)
    make_video(
        "<p>Notes on <strong>bearings</strong></p>",
        title="Zzz",
        collection=collection,
    )

    assert matches_collection(collection, search="turbines")
    assert matches_collection(collection, search="bearings")
