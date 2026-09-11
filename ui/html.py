"""
HTML sanitizing for rich-text description fields.

Collection and Video descriptions are authored as rich text in the OVS UI and
published to MIT Learn, which renders them with `dangerouslySetInnerHTML` after
running them through its own `nh3` allowlist during ETL. Two rules follow from
that:

1. OVS sanitizes on write, so the stored value is safe for OVS's own pages to
   render as HTML and no unsanitized markup ever reaches the public API.
2. The tags allowed here must be a *subset* of Learn's allowlist
   (`main.constants.ALLOWED_HTML_TAGS_WITH_LINKS` in mitodl/mit-learn), or
   formatting an author applies in OVS silently disappears on Learn - the worst
   possible failure mode for a content author. `ALLOWED_DESCRIPTION_TAGS` below
   is deliberately narrower than Learn's list, never wider.

Notably absent: heading tags. Learn's allowlist has no `h1`-`h6`, so the editor
does not offer headings (see static/js/lib/editor.js, which builds the toolbar
from the same vocabulary).
"""

import re

import nh3
from bs4 import BeautifulSoup

from ui.constants import DescriptionFormat

# Must stay a subset of Learn's ALLOWED_HTML_TAGS_WITH_LINKS.
ALLOWED_DESCRIPTION_TAGS = frozenset(
    {
        "a",
        "b",
        "blockquote",
        "br",
        "em",
        "i",
        "li",
        "ol",
        "p",
        "strong",
        "u",
        "ul",
    }
)

# Learn keeps only href and title on anchors and drops every other attribute, so
# anything we allowed beyond this would be lost in transit.
ALLOWED_DESCRIPTION_ATTRIBUTES = {"a": {"href", "title"}}

# nh3 defaults to a wider scheme list (including `ftp` and `data`). Descriptions
# are author-supplied links to further reading, so http(s) and mailto cover the
# real use and keep the surface small.
ALLOWED_URL_SCHEMES = frozenset({"http", "https", "mailto"})

# url_schemes only constrains *absolute* urls; nh3 passes relative ones through
# untouched, so without this a `//evil.example/x` href survives the scheme check
# and renders as an off-site link. Descriptions never need a relative link - they
# are published to MIT Learn, where a site-relative href would resolve against
# the wrong host anyway.
URL_RELATIVE_POLICY = "deny"


def sanitize_description(value):
    """
    Strip disallowed markup from a rich-text description.

    Args:
        value (str or None): the raw description, as submitted

    Returns:
        str: the sanitized description, or "" when there was nothing to keep.
            nh3 also rewrites anchors to carry rel="noopener noreferrer".
    """
    if not value:
        return ""
    return nh3.clean(
        value,
        tags=set(ALLOWED_DESCRIPTION_TAGS),
        attributes={
            tag: set(attrs) for tag, attrs in ALLOWED_DESCRIPTION_ATTRIBUTES.items()
        },
        url_schemes=set(ALLOWED_URL_SCHEMES),
        url_relative=URL_RELATIVE_POLICY,
    )


def attributes_in(value):
    """
    Return the attribute names actually present on tags in an HTML string.

    Parsed rather than pattern-matched: a regex over the source cannot tell an
    attribute from prose, and "Q&A with the class = fun" or "Register online =
    required" both look like attributes to one.

    Args:
        value (str): the HTML to inspect

    Returns:
        set: lowercased attribute names found on any tag
    """
    if not value:
        return set()
    soup = BeautifulSoup(value, "html5lib")
    found = set()
    for tag in soup.find_all(True):
        found.update(name.lower() for name in tag.attrs)
    return found


def tags_in(value):
    """
    Return the tag names actually present in an HTML string.

    Args:
        value (str): the HTML to inspect

    Returns:
        set: lowercased tag names
    """
    if not value:
        return set()
    soup = BeautifulSoup(value, "html5lib")
    # html5lib supplies html/head/body around a fragment; they are not the
    # author's markup.
    implied = {"html", "head", "body"}
    return {tag.name.lower() for tag in soup.find_all(True)} - implied


def description_to_text(value):
    """
    Flatten a rich-text description to plain text.

    For the consumers that cannot take markup at all - the YouTube description
    push in cloudsync.youtube, most importantly, where tags would be shown to
    viewers verbatim and would eat into YouTube's character budget.

    Block boundaries become newlines and list items gain a bullet, so a
    description that reads as a list still reads as a list once the tags are
    gone.

    Args:
        value (str or None): the description, as stored

    Returns:
        str: plain text with no markup and no HTML entities
    """
    if not value:
        return ""

    # BeautifulSoup rather than a regex: entities have to be decoded, and
    # `<p>a</p><p>b</p>` must not become "ab".
    soup = BeautifulSoup(value, "html5lib")

    for br in soup.find_all("br"):
        br.replace_with("\n")
    for item in soup.find_all("li"):
        item.insert_before("\n• ")
    for block in soup.find_all(["p", "blockquote", "ul", "ol"]):
        block.insert_after("\n\n")

    text = soup.get_text()
    # Collapse the runs of blank lines the substitutions above can leave behind,
    # and trim trailing spaces on each line.
    lines = [line.rstrip() for line in text.split("\n")]
    out = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


# A description "looks like HTML" if it opens one of the tags the editor can
# produce. Deliberately narrow: a description that merely mentions "<3" is prose.
#
# Only ever consulted at upgrade time, where an author sees the result in the
# editor before saving. Nothing renders on the strength of this guess - what a
# description *is* comes from Collection/Video.description_format, which is
# recorded rather than inferred.
#
# The tag has to be *well formed* to count. An earlier version of this ended in
# `[^>]*>`, which let `<b` in "Compare <b to a for the notes." run on until the
# `>` of some later tag and match the whole span as one enormous tag - so a
# plain-text description was mistaken for markup and sanitized, and nh3 dropped
# the words in between. What follows the tag name must therefore be the end of
# the tag, or the start of an attribute.
LOOKS_LIKE_HTML_RE = re.compile(
    r"</?(?:p|br|strong|em|b|i|u|ul|ol|li|a|blockquote)"
    r"(?:\s*/?>|\s+[a-zA-Z-]+\s*=)",
    re.IGNORECASE,
)

_ESCAPES = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"))


def looks_like_html(value):
    """
    Guess whether a description was written as markup.

    Args:
        value (str or None): the stored description

    Returns:
        bool: True if it opens a tag the editor can produce
    """
    return bool(value) and bool(LOOKS_LIKE_HTML_RE.search(value))


def plaintext_to_html(value):
    """
    Wrap plain text in the markup that renders it identically.

    Escaped first, so text is never reinterpreted as markup: `a <b to c` has to
    survive as those characters rather than opening a tag and swallowing the rest
    of the description. Blank lines become paragraphs and single newlines become
    `<br>`, because in plain text those carried the only structure there was.

    Args:
        value (str or None): plain-text description

    Returns:
        str: HTML rendering the same words with the same line structure
    """
    if not value:
        return ""
    text = value.strip()
    if not text:
        return ""
    for raw, escaped in _ESCAPES:
        text = text.replace(raw, escaped)
    # Normalize line endings before splitting so CRLF input doesn't leave a
    # stray \r inside the output.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = [block.strip("\n") for block in re.split(r"\n\s*\n", text)]
    return "".join(
        "<p>{}</p>".format(block.replace("\n", "<br>"))
        for block in blocks
        if block.strip()
    )


def upgrade_description(value):
    """
    Convert a plain-text description to the rich text equivalent.

    For the author-initiated upgrade in the edit dialog. Two kinds of value
    arrive here, and neither can be passed through untouched:

      * genuine plain text -> escaped and wrapped (`plaintext_to_html`).
      * markup someone pasted into the old plain-text field -> sanitized. These
        values were never checked against an allowlist, because the field was
        plain text and React escaped it at render, so a legacy description
        holding `onerror=` becomes live markup the moment it is rendered as
        rich text. It is cleaned here rather than trusted.

    Args:
        value (str or None): the stored plain-text description

    Returns:
        str: rich-text HTML, safe to render
    """
    if not value:
        return ""
    if looks_like_html(value):
        return sanitize_description(value)
    return plaintext_to_html(value)


def description_as_plain_text(value, description_format):
    """
    Flatten any stored description to plain text, whatever format it is in.

    For consumers that cannot take markup at all - the YouTube description push
    in cloudsync.youtube, where tags would be shown to viewers verbatim.

    A plain-text description is returned as-is rather than parsed: running it
    through the HTML flattener would read `a <b to c` as a tag and delete the
    rest of the description.

    Args:
        value (str or None): the stored description
        description_format (str): the row's DescriptionFormat

    Returns:
        str: plain text
    """
    if not value:
        return ""
    if description_format == DescriptionFormat.HTML:
        return description_to_text(value)
    return value


def description_as_html(value, description_format):
    """
    Render any stored description as HTML, whatever format it is in.

    For consumers that can only take markup - MIT Learn renders the public API's
    `description` with `dangerouslySetInnerHTML`, so a plain-text value sent
    as-is would lose its line breaks and be truncated at the first `<`.

    Plain text is escaped rather than upgraded: this is a read, and a read must
    not quietly reinterpret a legacy value as markup. `upgrade_description` is
    the only path that does that, and only when an author asks.

    Args:
        value (str or None): the stored description
        description_format (str): the row's DescriptionFormat

    Returns:
        str: HTML
    """
    if not value:
        return ""
    if description_format == DescriptionFormat.HTML:
        # Sanitized on write; see RichTextDescriptionMixin.
        return value
    return plaintext_to_html(value)
