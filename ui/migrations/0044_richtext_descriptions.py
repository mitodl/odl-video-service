"""
Convert existing plain-text Collection/Video descriptions to HTML.

Descriptions used to be plain text, rendered escaped by React. They are now
rich text rendered as markup, both on OVS's own pages and on MIT Learn - which
changes what the existing rows mean:

  * "Sessions 1 & 2" would render as "Sessions 1 " once `& 2` is read as the
    start of an entity, so every legacy value has to be HTML-escaped.
  * author-typed newlines carry structure that would collapse entirely, so
    blank-line-separated blocks become <p> and single newlines become <br>.

Rows are handled one of two ways, and neither is "left alone":

  * still plain text -> escaped and wrapped, as above.
  * already contains markup -> run through the allowlist. These values were
    never sanitized (the field was plain text, and React escaped it at render),
    so a legacy description holding `<script>` or `onerror=` would become live
    markup the moment the field is rendered with dangerouslySetInnerHTML. It has
    to be cleaned here, not merely skipped.

Running this twice is safe: escaping only happens on values with no markup, and
sanitizing is idempotent.
"""

import re

import nh3
from django.db import migrations

# Frozen copies of ui.html's allowlist. A migration must not import application
# code: this has to keep doing what it did when it was written, even after the
# allowlist changes.
MIGRATION_ALLOWED_TAGS = {
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
MIGRATION_ALLOWED_ATTRIBUTES = {"a": {"href", "title"}}
MIGRATION_URL_SCHEMES = {"http", "https", "mailto"}

# A row is "already HTML" if it opens one of the tags the editor can produce.
# Deliberately narrow - a description that merely mentions "<3" is plain text.
HTML_TAG_RE = re.compile(
    r"</?(?:p|br|strong|em|b|i|u|ul|ol|li|a|blockquote)\b[^>]*>",
    re.IGNORECASE,
)

ESCAPES = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"))


def plaintext_to_html(value):
    """
    Wrap a plain-text description in the markup that renders it identically.

    Args:
        value (str): the legacy plain-text description

    Returns:
        str: HTML with the text escaped, paragraphs split on blank lines and
            single newlines preserved as <br>
    """
    text = value.strip()
    if not text:
        return ""
    for raw, escaped in ESCAPES:
        text = text.replace(raw, escaped)
    # Normalize line endings before splitting so CRLF input doesn't leave \r
    # inside the output.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = [block.strip("\n") for block in re.split(r"\n\s*\n", text)]
    return "".join(
        "<p>{}</p>".format(block.replace("\n", "<br>")) for block in blocks if block.strip()
    )


def sanitize(value):
    """
    Strip disallowed markup from a legacy description that already holds HTML.

    Args:
        value (str): the stored description

    Returns:
        str: the description with only allowlisted markup left
    """
    return nh3.clean(
        value,
        tags=set(MIGRATION_ALLOWED_TAGS),
        attributes={tag: set(attrs) for tag, attrs in MIGRATION_ALLOWED_ATTRIBUTES.items()},
        url_schemes=set(MIGRATION_URL_SCHEMES),
        url_relative="deny",
    )


def convert(apps, schema_editor):
    """Rewrite plain-text descriptions as HTML"""
    for model_name in ("Collection", "Video"):
        model = apps.get_model("ui", model_name)
        updated = []
        for obj in model.objects.exclude(description="").exclude(description=None).iterator():
            if HTML_TAG_RE.search(obj.description):
                # Already markup, and never sanitized - clean it rather than
                # trusting it, because from now on it is rendered as HTML.
                converted = sanitize(obj.description)
            else:
                converted = plaintext_to_html(obj.description)
            if converted != obj.description:
                obj.description = converted
                updated.append(obj)
        if updated:
            model.objects.bulk_update(updated, ["description"], batch_size=500)


def unconvert(apps, schema_editor):
    """
    Turn the markup back into plain text.

    Reverses `convert` exactly for values it produced. Rich text an author has
    written since is flattened instead: formatting is lost, but the words are
    kept and a link keeps its target as "text (url)" - dropping the tag alone
    would discard the url irrecoverably, which is the one thing a rollback must
    not do.
    """
    for model_name in ("Collection", "Video"):
        model = apps.get_model("ui", model_name)
        updated = []
        for obj in model.objects.exclude(description="").exclude(description=None).iterator():
            if not HTML_TAG_RE.search(obj.description):
                continue
            text = obj.description
            # Keep link targets: "<a href="u">t</a>" -> "t (u)". Skipped when the
            # text already is the url, which is how most authors write them.
            text = re.sub(
                r'<a\b[^>]*\bhref="([^"]*)"[^>]*>(.*?)</a>',
                lambda match: (
                    match.group(2)
                    if match.group(1).strip() in ("", match.group(2).strip())
                    else "{} ({})".format(match.group(2), match.group(1))
                ),
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            text = re.sub(r"</p>\s*<p>", "\n\n", text)
            text = re.sub(r"</li>\s*<li>", "\n", text)
            text = re.sub(r"<br\s*/?>", "\n", text)
            text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)
            for raw, escaped in reversed(ESCAPES):
                text = text.replace(escaped, raw)
            obj.description = text.strip()
            updated.append(obj)
        if updated:
            model.objects.bulk_update(updated, ["description"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("ui", "0043_fail_stuck_uploading_videos"),
    ]

    operations = [
        migrations.RunPython(convert, unconvert),
    ]
