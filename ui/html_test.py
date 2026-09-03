"""
Tests for rich-text description sanitizing
"""

import importlib

import pytest

from ui.html import (
    ALLOWED_DESCRIPTION_ATTRIBUTES,
    ALLOWED_DESCRIPTION_TAGS,
    attributes_in,
    description_to_text,
    sanitize_description,
    tags_in,
)

# A copy of mit-learn's main.constants.ALLOWED_HTML_TAGS_WITH_LINKS. Learn's ETL
# runs every OVS description through nh3 with this list, so anything OVS allows
# but Learn does not is formatting that silently disappears between authoring and
# publication. If Learn's list changes, update this copy and the test below will
# say whether we are still safe.
LEARN_ALLOWED_HTML_TAGS_WITH_LINKS = {
    "a",
    "b",
    "blockquote",
    "br",
    "caption",
    "center",
    "cite",
    "code",
    "div",
    "em",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "q",
    "small",
    "span",
    "strike",
    "strong",
    "sub",
    "sup",
    "u",
    "ul",
}
LEARN_ALLOWED_HTML_ATTRIBUTES_WITH_LINKS = {"a": {"href", "title"}}


def test_allowlist_is_subset_of_learn():
    """
    Every tag OVS accepts must survive Learn's sanitizer.

    This is the contract test for the whole feature: a tag allowed here but not
    there is formatting an author applies successfully in OVS and then cannot
    find on Learn.
    """
    assert set(ALLOWED_DESCRIPTION_TAGS) <= LEARN_ALLOWED_HTML_TAGS_WITH_LINKS


def test_allowed_attributes_are_subset_of_learn():
    """Attributes OVS keeps must also survive Learn's sanitizer"""
    for tag, attrs in ALLOWED_DESCRIPTION_ATTRIBUTES.items():
        assert set(attrs) <= LEARN_ALLOWED_HTML_ATTRIBUTES_WITH_LINKS.get(tag, set())


def test_no_heading_tags_offered():
    """
    Learn's allowlist has no h1-h6, so OVS must not accept them either - a
    heading would be stripped in transit and the author would never know.
    """
    assert not {"h1", "h2", "h3", "h4", "h5", "h6"} & set(ALLOWED_DESCRIPTION_TAGS)


@pytest.mark.parametrize(
    "value",
    [
        "<p>plain paragraph</p>",
        "<p>with <strong>bold</strong> and <em>italic</em></p>",
        "<ul><li>one</li><li>two</li></ul>",
        "<ol><li>first</li></ol>",
        "<p>line<br>break</p>",
        "<blockquote>quoted</blockquote>",
    ],
)
def test_allowed_markup_survives(value):
    """Markup the editor can produce round-trips unchanged"""
    assert sanitize_description(value) == value


def test_links_survive_and_gain_rel():
    """A link keeps its href and picks up rel from nh3"""
    result = sanitize_description('<p><a href="https://learn.mit.edu/x">go</a></p>')
    assert 'href="https://learn.mit.edu/x"' in result
    assert 'rel="noopener noreferrer"' in result
    assert ">go</a>" in result


def test_mailto_links_survive():
    """mailto is an allowed scheme"""
    assert 'href="mailto:ovs@mit.edu"' in sanitize_description(
        '<p><a href="mailto:ovs@mit.edu">mail</a></p>'
    )


@pytest.mark.parametrize(
    ("value", "must_not_contain"),
    [
        ("<script>alert(1)</script>", "script"),
        ('<img src="x" onerror="alert(1)">', "img"),
        ('<p style="color:red">red text</p>', "style="),
        ('<p class="ql-align-center">centered text</p>', "class="),
        ("<h2>a heading</h2>", "<h2"),
        ('<iframe src="https://evil.example"></iframe>', "iframe"),
        ('<a href="javascript:alert(1)">x</a>', "javascript"),
        ('<a href="data:text/html;base64,eHl6">x</a>', "data:"),
        ("<p>ok</p><style>body{display:none}</style>", "display:none"),
    ],
)
def test_disallowed_markup_removed(value, must_not_contain):
    """Anything outside the allowlist is stripped"""
    assert must_not_contain not in sanitize_description(value)


def test_text_content_is_kept_when_tag_is_stripped():
    """Stripping a tag must not throw away the author's words"""
    assert "heading text" in sanitize_description("<h2>heading text</h2>")


@pytest.mark.parametrize("value", [None, "", "   "])
def test_empty_values(value):
    """Empty input sanitizes to an empty string, never None"""
    result = sanitize_description(value)
    assert isinstance(result, str)
    assert result.strip() == ""


def test_double_sanitize_is_stable():
    """Sanitizing an already-sanitized value changes nothing"""
    once = sanitize_description('<p>hi <a href="https://x.mit.edu">link</a></p>')
    assert sanitize_description(once) == once


class TestDescriptionToText:
    """description_to_text, used for consumers that cannot take markup"""

    def test_entities_are_decoded(self):
        """&amp; becomes & - YouTube would otherwise show the entity"""
        assert description_to_text("<p>Sessions 1 &amp; 2</p>") == "Sessions 1 & 2"

    def test_paragraphs_are_separated(self):
        """Adjacent paragraphs must not run together"""
        assert description_to_text("<p>one</p><p>two</p>") == "one\n\ntwo"

    def test_list_items_become_bullets(self):
        """A list should still read as a list without its tags"""
        result = description_to_text("<p>Next:</p><ul><li>one</li><li>two</li></ul>")
        assert result == "Next:\n\n• one\n• two"

    def test_link_text_is_kept(self):
        """Link text survives; the href is dropped"""
        result = description_to_text(
            '<p>See <a href="https://x.mit.edu">the docs</a></p>'
        )
        assert result == "See the docs"

    def test_line_breaks(self):
        """<br> becomes a newline"""
        assert description_to_text("<p>a<br>b</p>") == "a\nb"

    def test_no_markup_remains(self):
        """No angle brackets survive, whatever went in"""
        assert "<" not in description_to_text("<p><strong>a</strong> <em>b</em></p>")

    @pytest.mark.parametrize("value", [None, ""])
    def test_empty(self, value):
        """Empty input gives an empty string"""
        assert description_to_text(value) == ""

    def test_plain_text_passes_through(self):
        """Legacy plain-text descriptions are unchanged"""
        assert description_to_text("just some text") == "just some text"


class TestPlaintextMigration:
    """The 0044 data migration's plain-text-to-HTML conversion"""

    @staticmethod
    def _module():
        return importlib.import_module("ui.migrations.0044_richtext_descriptions")

    def test_escapes_ampersand(self):
        """
        "Sessions 1 & 2" must not become a broken entity once the field is
        rendered as markup.
        """
        module = self._module()
        assert module.plaintext_to_html("Sessions 1 & 2") == "<p>Sessions 1 &amp; 2</p>"

    def test_escapes_angle_brackets(self):
        """Legacy text containing < or > is escaped, not interpreted"""
        module = self._module()
        assert module.plaintext_to_html("x < y") == "<p>x &lt; y</p>"

    def test_blank_lines_become_paragraphs(self):
        """Author-typed paragraph breaks are preserved"""
        module = self._module()
        assert module.plaintext_to_html("one\n\ntwo") == "<p>one</p><p>two</p>"

    def test_single_newlines_become_br(self):
        """Single newlines are line breaks within a paragraph"""
        module = self._module()
        assert module.plaintext_to_html("one\ntwo") == "<p>one<br>two</p>"

    def test_crlf_is_normalized(self):
        """Windows line endings must not leave \\r inside the output"""
        module = self._module()
        assert "\r" not in module.plaintext_to_html("one\r\n\r\ntwo")

    @pytest.mark.parametrize("value", ["", "   ", "\n\n"])
    def test_empty(self, value):
        """Nothing to convert gives an empty string"""
        module = self._module()
        assert module.plaintext_to_html(value) == ""

    def test_output_survives_the_sanitizer(self):
        """
        Whatever the migration writes must itself be valid per the allowlist,
        or the first save after the migration would change the stored value.
        """
        module = self._module()
        converted = module.plaintext_to_html("A & B\nsecond line\n\nnew para")
        assert sanitize_description(converted) == converted

    def test_already_html_is_detected(self):
        """Rows already holding markup are skipped, so nothing double-escapes"""
        module = self._module()
        assert module.HTML_TAG_RE.search("<p>already</p>")
        assert module.HTML_TAG_RE.search('<a href="https://x">link</a>')

    @pytest.mark.parametrize(
        "value", ["I <3 this", "a > b", "plain text", "5 < 6 & 7 > 2"]
    )
    def test_plain_text_not_mistaken_for_html(self, value):
        """A description that merely mentions angle brackets is still plain text"""
        module = self._module()
        assert not module.HTML_TAG_RE.search(value)


@pytest.mark.django_db
class TestMigrationAgainstRows:
    """The 0044 migration applied to real Collection/Video rows"""

    @staticmethod
    def _migration():
        return importlib.import_module("ui.migrations.0044_richtext_descriptions")

    def test_converts_plain_text_rows(self):
        """A legacy plain-text description becomes HTML"""
        from django.apps import apps

        from ui.factories import CollectionFactory, VideoFactory

        collection = CollectionFactory.create(
            description="Sessions 1 & 2\n\nSecond para"
        )
        video = VideoFactory.create(description="Line one\nLine two")

        self._migration().convert(apps, None)

        collection.refresh_from_db()
        video.refresh_from_db()
        assert collection.description == "<p>Sessions 1 &amp; 2</p><p>Second para</p>"
        assert video.description == "<p>Line one<br>Line two</p>"

    def test_does_not_escape_existing_html(self):
        """
        Rows already holding markup are sanitized, never escaped - running this
        after some rows have been edited in the new editor must not turn their
        tags into visible text.
        """
        from django.apps import apps

        from ui.factories import VideoFactory

        html = (
            '<p>Already <strong>rich</strong> <a href="https://x.mit.edu">text</a></p>'
        )
        video = VideoFactory.create(description=html)

        self._migration().convert(apps, None)

        video.refresh_from_db()
        assert "&lt;" not in video.description
        assert "<strong>rich</strong>" in video.description
        assert 'href="https://x.mit.edu"' in video.description
        # sanitizing is the only thing that changed it, and only by adding rel
        assert video.description == sanitize_description(html)

    def test_is_idempotent(self):
        """Running the migration twice leaves the same value"""
        from django.apps import apps

        from ui.factories import VideoFactory

        video = VideoFactory.create(description="A & B")
        migration = self._migration()
        migration.convert(apps, None)
        video.refresh_from_db()
        once = video.description
        migration.convert(apps, None)
        video.refresh_from_db()
        assert video.description == once

    def test_reverse_restores_plain_text(self):
        """The migration is reversible"""
        from django.apps import apps

        from ui.factories import VideoFactory

        video = VideoFactory.create(description="Sessions 1 & 2\n\nSecond para")
        migration = self._migration()
        migration.convert(apps, None)
        migration.unconvert(apps, None)
        video.refresh_from_db()
        assert video.description == "Sessions 1 & 2\n\nSecond para"

    def test_empty_descriptions_untouched(self):
        """Rows with no description are left as they are"""
        from django.apps import apps

        from ui.factories import VideoFactory

        video = VideoFactory.create(description="")
        self._migration().convert(apps, None)
        video.refresh_from_db()
        assert video.description == ""


class TestRelativeHrefs:
    """url_schemes only constrains absolute urls; relative ones need denying"""

    @pytest.mark.parametrize(
        "href", ["//evil.example/x", "/local/path", "../up", "path/only"]
    )
    def test_relative_hrefs_lose_their_target(self, href):
        """
        A protocol-relative href would render as an off-site link, and a
        site-relative one resolves against the wrong host once published to Learn.
        """
        result = sanitize_description(f'<a href="{href}">x</a>')
        assert "href" not in result
        assert ">x</a>" in result

    def test_absolute_https_survives(self):
        """The allowed schemes are unaffected"""
        assert 'href="https://ok.mit.edu"' in sanitize_description(
            '<a href="https://ok.mit.edu">x</a>'
        )


class TestParsedInspection:
    """attributes_in / tags_in, used by the admin form"""

    @pytest.mark.parametrize(
        "prose",
        [
            "<p>Q&A with the class = fun, style = casual</p>",
            "<p>Register online = required & free</p>",
            "<p>id = 7 and target = 2026</p>",
        ],
    )
    def test_prose_is_not_mistaken_for_attributes(self, prose):
        """
        A regex over the source reads these as attributes and refuses good
        prose. Parsing does not.
        """
        assert attributes_in(prose) == set()

    def test_real_attributes_are_found(self):
        """Actual attributes are reported"""
        assert attributes_in('<p style="color:red" class="x">y</p>') == {
            "style",
            "class",
        }

    def test_tags_exclude_the_implied_document_wrapper(self):
        """html5lib adds html/head/body around a fragment; they are not markup"""
        assert tags_in("<h2>a</h2><p>b</p>") == {"h2", "p"}

    def test_empty(self):
        """Nothing in, nothing out"""
        assert attributes_in("") == set()
        assert tags_in(None) == set()


@pytest.mark.django_db
class TestMigrationSanitizesLegacyMarkup:
    """
    Legacy descriptions holding markup were never sanitized - the field was
    plain text and React escaped it at render. Once it is rendered as HTML they
    are live markup, so the migration has to clean them, not skip them.
    """

    @staticmethod
    def _migration():
        return importlib.import_module("ui.migrations.0044_richtext_descriptions")

    @pytest.mark.parametrize(
        ("legacy", "must_not_contain"),
        [
            ("<p>hi</p><script>alert(1)</script>", "script"),
            ("Read <b>this</b> <img src=x onerror=alert(1)>", "onerror"),
            ('<p onmouseover="alert(1)">hover</p>', "onmouseover"),
            ('<a href="javascript:alert(1)">x</a>', "javascript"),
            ('<a href="//evil.example/x">x</a>', "evil.example"),
        ],
    )
    def test_legacy_payloads_are_stripped(self, legacy, must_not_contain):
        """A legacy row holding a payload must not survive the migration"""
        from django.apps import apps

        from ui.factories import VideoFactory

        video = VideoFactory.create(description=legacy)
        self._migration().convert(apps, None)
        video.refresh_from_db()
        assert must_not_contain not in video.description

    def test_legitimate_legacy_markup_is_preserved(self):
        """Cleaning must not throw away markup that was already fine"""
        from django.apps import apps

        from ui.factories import VideoFactory

        video = VideoFactory.create(
            description='<p>legit <a href="https://x.mit.edu">link</a></p>'
        )
        self._migration().convert(apps, None)
        video.refresh_from_db()
        assert "<p>legit " in video.description
        assert 'href="https://x.mit.edu"' in video.description

    def test_every_row_is_safe_afterwards(self):
        """
        The invariant that matters: after the migration, no description differs
        from its own sanitized form.
        """
        from django.apps import apps

        from ui.factories import CollectionFactory, VideoFactory

        CollectionFactory.create(description="<p>ok</p><script>bad()</script>")
        VideoFactory.create(description="plain & simple")
        VideoFactory.create(description='<p onclick="x()">handler</p>')

        self._migration().convert(apps, None)

        from ui.models import Collection, Video

        for model in (Collection, Video):
            for obj in model.objects.exclude(description="").exclude(description=None):
                assert obj.description == sanitize_description(obj.description), (
                    f"{model.__name__} {obj.pk} is not sanitized"
                )


@pytest.mark.django_db
class TestMigrationReverseKeepsLinkTargets:
    """A rollback must not discard urls - they are unrecoverable"""

    @staticmethod
    def _migration():
        return importlib.import_module("ui.migrations.0044_richtext_descriptions")

    def test_href_is_kept_alongside_the_text(self):
        """<a href="u">t</a> becomes "t (u)" rather than just "t\""""
        from django.apps import apps

        from ui.factories import VideoFactory

        video = VideoFactory.create(
            description='<p>See <a href="https://climate.mit.edu">the primers</a></p>'
        )
        self._migration().unconvert(apps, None)
        video.refresh_from_db()
        assert "the primers (https://climate.mit.edu)" in video.description

    def test_list_items_do_not_run_together(self):
        """</li><li> is a line boundary, not nothing"""
        from django.apps import apps

        from ui.factories import VideoFactory

        video = VideoFactory.create(description="<ul><li>one</li><li>two</li></ul>")
        self._migration().unconvert(apps, None)
        video.refresh_from_db()
        assert "onetwo" not in video.description
        assert "one\ntwo" in video.description

    def test_a_link_whose_text_is_the_url_is_not_duplicated(self):
        """No "https://x (https://x)\""""
        from django.apps import apps

        from ui.factories import VideoFactory

        video = VideoFactory.create(
            description='<p><a href="https://x.mit.edu">https://x.mit.edu</a></p>'
        )
        self._migration().unconvert(apps, None)
        video.refresh_from_db()
        assert video.description == "https://x.mit.edu"
