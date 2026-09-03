"""
Tests for rich-text description sanitizing
"""

import pytest

from ui.constants import DescriptionFormat
from ui.html import (
    ALLOWED_DESCRIPTION_ATTRIBUTES,
    ALLOWED_DESCRIPTION_TAGS,
    attributes_in,
    description_as_html,
    description_to_text,
    looks_like_html,
    plaintext_to_html,
    sanitize_description,
    tags_in,
    upgrade_description,
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


class TestPlaintextToHtml:
    """Rendering a plain-text description as the markup that looks the same"""

    def test_escapes_ampersand(self):
        """An & is escaped so it cannot be read as the start of an entity"""
        assert plaintext_to_html("Sessions 1 & 2") == "<p>Sessions 1 &amp; 2</p>"

    def test_escapes_angle_brackets(self):
        """
        Text containing < is escaped, not interpreted.

        Left alone this is the one that silently eats content: a browser reads
        `<b to a` as an unterminated tag and drops everything after it.
        """
        assert plaintext_to_html("x < y") == "<p>x &lt; y</p>"
        assert (
            plaintext_to_html("Compare <b to a. Then stop.")
            == "<p>Compare &lt;b to a. Then stop.</p>"
        )

    def test_blank_lines_become_paragraphs(self):
        """Author-typed paragraph breaks are preserved"""
        assert plaintext_to_html("one\n\ntwo") == "<p>one</p><p>two</p>"

    def test_single_newlines_become_br(self):
        """Single newlines are line breaks within a paragraph"""
        assert plaintext_to_html("one\ntwo") == "<p>one<br>two</p>"

    def test_crlf_is_normalized(self):
        """Windows line endings must not leave \\r inside the output"""
        assert "\r" not in plaintext_to_html("one\r\n\r\ntwo")

    @pytest.mark.parametrize("value", ["", "   ", "\n\n", None])
    def test_empty(self, value):
        """Nothing to convert gives an empty string"""
        assert plaintext_to_html(value) == ""

    def test_output_survives_the_sanitizer(self):
        """
        What this produces must itself be valid per the allowlist, or the first
        save after an upgrade would change the stored value again.
        """
        converted = plaintext_to_html("A & B\nsecond line\n\nnew para")
        assert sanitize_description(converted) == converted


class TestLooksLikeHtml:
    """The guess used only at upgrade time, where an author sees the result"""

    @pytest.mark.parametrize(
        "value",
        [
            "<p>already</p>",
            '<a href="https://x">link</a>',
            "text with <br> in it",
            "<STRONG>upper</STRONG>",
        ],
    )
    def test_markup_is_detected(self, value):
        """A value opening a tag the editor can produce reads as markup"""
        assert looks_like_html(value)

    @pytest.mark.parametrize(
        "value",
        [
            "I <3 this",
            "a > b",
            "plain text",
            "5 < 6 & 7 > 2",
            "",
            None,
            "<h2>only</h2>",
            # A regression. This used to match: the pattern ended in `[^>]*>`,
            # so `<b` ran on until the `>` of the img tag further down and the
            # whole span matched as one enormous tag. The description was then
            # taken for markup and sanitized, and nh3 dropped every word
            # between the two - "Compare <b></b>" was all that survived.
            'Compare <b to a for the notes.\n\n<img src=x onerror="x">',
            "Compare <b to a. Then 5 > 3.",
        ],
    )
    def test_plain_text_is_not(self, value):
        """
        A description that merely mentions angle brackets is still plain text.

        `<h2>` is in here deliberately: the editor cannot produce it, so a value
        holding only headings is treated as text and gets escaped rather than
        upgraded into markup the allowlist would drop anyway.
        """
        assert not looks_like_html(value)


class TestUpgradeDescription:
    """The author-initiated conversion from plain text to rich text"""

    def test_converts_plain_text(self):
        """Line structure survives the upgrade"""
        assert (
            upgrade_description("Sessions 1 & 2\n\nSecond para")
            == "<p>Sessions 1 &amp; 2</p><p>Second para</p>"
        )

    def test_does_not_escape_existing_markup(self):
        """
        A value that already holds markup is sanitized, never escaped.

        Someone pasted HTML into the old plain-text field; upgrading it should
        give them their formatting, not their tags as visible text.
        """
        html = (
            '<p>Already <strong>rich</strong> <a href="https://x.mit.edu">text</a></p>'
        )
        upgraded = upgrade_description(html)
        assert "&lt;" not in upgraded
        assert "<strong>rich</strong>" in upgraded
        assert 'href="https://x.mit.edu"' in upgraded
        # sanitizing is the only thing that changed it, and only by adding rel
        assert upgraded == sanitize_description(html)

    def test_is_idempotent(self):
        """Upgrading an upgraded value leaves it alone"""
        once = upgrade_description("A & B")
        assert upgrade_description(once) == once

    def test_does_not_lose_words_to_a_stray_angle_bracket(self):
        """
        The regression worth a test of its own: a plain-text description holding
        `<b` and, further on, a `>` was taken for markup, and sanitizing then
        deleted every word between the two.
        """
        upgraded = upgrade_description(
            'Compare <b to a for the notes.\n\n<img src=x onerror="x">'
        )
        assert "Compare &lt;b to a for the notes." in upgraded
        assert "img src=x" in upgraded
        assert "<b>" not in upgraded

    @pytest.mark.parametrize("value", ["", None])
    def test_empty(self, value):
        """Nothing to upgrade gives an empty string"""
        assert upgrade_description(value) == ""

    @pytest.mark.parametrize(
        ("value", "must_not_contain"),
        [
            ("<p>hi</p><script>alert(1)</script>", "script"),
            ("Read <b>this</b> <img src=x onerror=alert(1)>", "onerror"),
            ('<p onmouseover="alert(1)">hover</p>', "onmouseover"),
            ('<a href="javascript:alert(1)">x</a>', "javascript"),
        ],
    )
    def test_legacy_payloads_are_cleaned(self, value, must_not_contain):
        """
        Legacy markup was never checked against the allowlist - the field was
        plain text and React escaped it at render - so upgrading a row is the
        moment it has to be cleaned, not trusted.
        """
        assert must_not_contain not in upgrade_description(value).lower()


class TestDescriptionAsHtml:
    """Serving any stored description to a consumer that can only take markup"""

    def test_rich_text_is_passed_through(self):
        """Already markup, already sanitized on write"""
        html = "<p>a <strong>b</strong></p>"
        assert description_as_html(html, DescriptionFormat.HTML) == html

    def test_plain_text_is_escaped_not_upgraded(self):
        """
        A read must not reinterpret a legacy value as markup.

        Escaping keeps every character the author typed, and keeps a stored
        payload inert; `upgrade_description` is the only path that promotes text
        to markup, and only when an author asks for it.
        """
        assert (
            description_as_html("a <b to c", DescriptionFormat.TEXT)
            == "<p>a &lt;b to c</p>"
        )

    def test_plain_text_keeps_its_line_breaks(self):
        """The breaks are the only structure plain text had"""
        assert (
            description_as_html("one\ntwo", DescriptionFormat.TEXT)
            == "<p>one<br>two</p>"
        )

    def test_stored_payload_in_a_text_row_is_inert(self):
        """
        The format defaults to text, so this is the shape every pre-existing row
        has - including any that happen to hold markup.
        """
        served = description_as_html(
            '<img src=x onerror="alert(1)">', DescriptionFormat.TEXT
        )
        # The angle brackets are escaped, so this is text on the page rather
        # than an element with a handler on it.
        assert served == '<p>&lt;img src=x onerror="alert(1)"&gt;</p>'
        assert "<img" not in served

    @pytest.mark.parametrize("value", ["", None])
    def test_empty(self, value):
        """Nothing stored gives an empty string"""
        assert description_as_html(value, DescriptionFormat.TEXT) == ""


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
