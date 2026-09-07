// @flow
import { assert } from "chai"

import { plainTextToHtml } from "./description"

describe("plainTextToHtml", () => {
  /*
   * Mirrors ui/html_test.py's coverage of `plaintext_to_html`. The two have to
   * agree: a description converted here (a collection that does not exist yet)
   * and one converted on the server (every other case) must come out the same,
   * or an author sees a different result depending on when they clicked.
   */

  it("returns empty for nothing to convert", () => {
    assert.equal(plainTextToHtml(""), "")
    assert.equal(plainTextToHtml(null), "")
    assert.equal(plainTextToHtml(undefined), "")
    assert.equal(plainTextToHtml("   \n  \n "), "")
  })

  it("wraps a single line in a paragraph", () => {
    assert.equal(plainTextToHtml("Lecture notes"), "<p>Lecture notes</p>")
  })

  it("makes a paragraph of each blank-line-separated block", () => {
    assert.equal(
      plainTextToHtml("First para\n\nSecond para"),
      "<p>First para</p><p>Second para</p>"
    )
  })

  it("keeps a single newline as a line break", () => {
    // The blank line the author typed is the whole point: opening plain text in
    // the editor without this collapses it and the structure is gone.
    assert.equal(
      plainTextToHtml("Line one\nLine two"),
      "<p>Line one<br>Line two</p>"
    )
  })

  it("escapes text that would otherwise be read as markup", () => {
    // `Compare <b to a` is the case that motivated recording the format rather
    // than converting the table: read as HTML it truncates at the `<`.
    assert.equal(
      plainTextToHtml("Compare <b to a"),
      "<p>Compare &lt;b to a</p>"
    )
  })

  it("escapes an ampersand once, not twice", () => {
    assert.equal(plainTextToHtml("Q&A after"), "<p>Q&amp;A after</p>")
  })

  it("escapes markup the author pasted rather than trusting it", () => {
    // Nothing here is a stored legacy value to be salvaged - it is text typed
    // into a textarea moments ago, and escaping it is what makes it safe to
    // hand to an editor that renders its value as markup.
    assert.equal(
      plainTextToHtml('<img src=x onerror="alert(1)">'),
      '<p>&lt;img src=x onerror="alert(1)"&gt;</p>'
    )
  })

  it("normalizes CRLF so no stray carriage return survives", () => {
    assert.equal(
      plainTextToHtml("Line one\r\n\r\nLine two"),
      "<p>Line one</p><p>Line two</p>"
    )
  })

  it("drops a run of blank lines rather than making empty paragraphs", () => {
    assert.equal(
      plainTextToHtml("First\n\n\n\nSecond"),
      "<p>First</p><p>Second</p>"
    )
  })
})
