// @flow
/*
 * Plain-text to rich-text conversion, for the one case the server cannot do it.
 *
 * Converting a description is the server's job (`ui.html.upgrade_description`),
 * because it is the only place that knows how to clean markup someone once
 * pasted into the old plain-text field. A collection that has not been created
 * yet has no row to PATCH, so there is nothing to ask - and the value in hand
 * cannot simply be relabelled as rich text either:
 *
 *   * TipTap would parse it as HTML, and every blank line the author typed
 *     between paragraphs would collapse into a single space;
 *   * `RichTextEditor` renders the current value as markup until its chunk
 *     loads, so whatever the author typed would be injected into the page
 *     unescaped - including a `<img src=x onerror=...>` they pasted themselves.
 *
 * So the same escape-and-wrap that `ui.html.plaintext_to_html` does is done
 * here, and the two must stay in step. This deliberately does *not* reimplement
 * the sanitizing half of `upgrade_description`: it does not need it. There is no
 * stored legacy value to distrust, and escaping is what makes the result safe.
 */

// Order matters: `&` first, or the ampersands introduced by the other two get
// escaped a second time and render as "&amp;lt;".
const ESCAPES = [
  [/&/g, "&amp;"],
  [/</g, "&lt;"],
  [/>/g, "&gt;"]
]

/**
 * Wrap plain text in the markup that renders it identically.
 *
 * Mirrors `ui.html.plaintext_to_html`: text is escaped so it is never
 * reinterpreted as markup, blank lines become paragraphs, and single newlines
 * become `<br>` - in plain text those carried the only structure there was.
 */
export const plainTextToHtml = (value: ?string): string => {
  let text = (value || "").trim()
  if (!text) {
    return ""
  }
  ESCAPES.forEach(([pattern, replacement]) => {
    text = text.replace(pattern, replacement)
  })
  // Normalize line endings before splitting, so CRLF input does not leave a
  // stray \r inside the output.
  text = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n")
  return text
    .split(/\n\s*\n/)
    .map(block => block.replace(/^\n+|\n+$/g, ""))
    .filter(block => block.trim())
    .map(block => `<p>${block.replace(/\n/g, "<br>")}</p>`)
    .join("")
}
