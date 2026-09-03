// @flow
import { assert } from "chai"

import {
  TOOLBAR_BUTTONS,
  applyLink,
  createEditor,
  normalizeHref,
  normalizeHtml,
  runCommand
} from "./editor"

// Every tag the editor can emit has to survive MIT Learn's nh3 allowlist, which
// drops all attributes except href/title and has no heading tags. This mirrors
// ALLOWED_DESCRIPTION_TAGS in ui/html.py.
const ALLOWED_TAGS = [
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
  "ul"
]

const tagsIn = (html: string): Array<string> => {
  const found = html.match(/<([a-zA-Z][a-zA-Z0-9]*)/g) || []
  return [...new Set(found.map(match => match.slice(1).toLowerCase()))]
}

describe("editor lib", () => {
  describe("normalizeHtml", () => {
    it("treats an empty document as an empty value", () => {
      // TipTap serializes an empty doc as "<p></p>", which would otherwise be
      // stored as a non-empty description and render as a blank line.
      assert.equal(normalizeHtml("<p></p>"), "")
      assert.equal(normalizeHtml(""), "")
    })

    it("leaves real content alone", () => {
      assert.equal(normalizeHtml("<p>hi</p>"), "<p>hi</p>")
    })
  })

  describe("normalizeHref", () => {
    it("keeps http, https and mailto", () => {
      assert.equal(
        normalizeHref("https://learn.mit.edu"),
        "https://learn.mit.edu"
      )
      assert.equal(
        normalizeHref("http://learn.mit.edu"),
        "http://learn.mit.edu"
      )
      assert.equal(normalizeHref("mailto:ovs@mit.edu"), "mailto:ovs@mit.edu")
    })

    it("assumes https for a scheme-less host, which is how authors type URLs", () => {
      assert.equal(
        normalizeHref("learn.mit.edu/c/x"),
        "https://learn.mit.edu/c/x"
      )
    })

    it("trims surrounding whitespace", () => {
      assert.equal(normalizeHref("  https://x.mit.edu  "), "https://x.mit.edu")
    })

    for (const ok of [
      ["example.com?utm=1", "https://example.com?utm=1"],
      ["example.com#section", "https://example.com#section"],
      ["example.com:8080/x", "https://example.com:8080/x"],
      ["learn.mit.edu", "https://learn.mit.edu"]
    ]) {
      it(`accepts ${ok[0]}, which authors paste routinely`, () => {
        assert.equal(normalizeHref(ok[0]), ok[1])
      })
    }

    for (const bad of [
      "javascript:alert(1)",
      "data:text/html;base64,eHl6",
      "ftp://files.mit.edu",
      "not a url",
      "",
      "   "
    ]) {
      it(`rejects ${JSON.stringify(bad)}`, () => {
        assert.isNull(normalizeHref(bad))
      })
    }
  })

  describe("TOOLBAR_BUTTONS", () => {
    it("offers no heading control", () => {
      // Learn's allowlist has no h1-h6, so a heading button would appear to work
      // in OVS and then lose the formatting in transit.
      const names = TOOLBAR_BUTTONS.map(button => button.name)
      assert.notInclude(names, "heading")
      TOOLBAR_BUTTONS.forEach(button => {
        assert.notMatch(button.name, /^h[1-6]$/)
      })
    })

    it("gives every button a title for the accessible name", () => {
      TOOLBAR_BUTTONS.forEach(button => {
        assert.isString(button.title)
        assert.isNotEmpty(button.title)
      })
    })

    it("uses Material Icons ligatures, the set already loaded app-wide", () => {
      // Icons rather than "B"/"1. List" text, so the controls look like the ones
      // in every word processor. Ligature names must be lowercase with
      // underscores or the font renders the literal text.
      TOOLBAR_BUTTONS.forEach(button => {
        assert.match(button.icon, /^[a-z][a-z0-9_]*$/, button.name)
      })
      const icons = TOOLBAR_BUTTONS.map(b => b.icon)
      assert.deepEqual(icons, [
        "format_bold",
        "format_italic",
        "format_list_bulleted",
        "format_list_numbered",
        "link",
        "link_off"
      ])
    })
  })

  describe("with a live editor", () => {
    let element, editor, changes

    beforeEach(() => {
      element = document.createElement("div")
      document.body.appendChild(element)
      changes = []
      editor = createEditor(element, "<p>hello</p>", html => changes.push(html))
    })

    afterEach(() => {
      editor.destroy()
      if (element.parentNode) {
        element.parentNode.removeChild(element)
      }
    })

    it("loads the initial content", () => {
      assert.equal(editor.getHTML(), "<p>hello</p>")
    })

    it("reports changes as serialized HTML", () => {
      editor.commands.setContent("<p>changed</p>")
      assert.deepEqual(changes, ["<p>changed</p>"])
    })

    it("emits nothing but allowed tags for every toolbar command", () => {
      editor.commands.setContent("<p>text</p>")
      editor.commands.selectAll()
      runCommand(editor, "bold")
      runCommand(editor, "italic")
      runCommand(editor, "bulletList")
      applyLink(editor, "https://learn.mit.edu")
      const html = editor.getHTML()
      tagsIn(html).forEach(tag => {
        assert.include(
          ALLOWED_TAGS,
          tag,
          `editor emitted <${tag}>, which Learn strips`
        )
      })
    })

    it("produces <ul> for a bulleted list, not an attributed <ol>", () => {
      // Quill 2 encodes bullets as <ol><li data-list="bullet">, which Learn
      // renders numbered because it drops attributes. This asserts we don't.
      editor.commands.setContent("<p>item</p>")
      editor.commands.selectAll()
      runCommand(editor, "bulletList")
      const html = editor.getHTML()
      assert.include(html, "<ul>")
      assert.notInclude(html, "data-list")
    })

    it("produces <ol> for a numbered list", () => {
      editor.commands.setContent("<p>item</p>")
      editor.commands.selectAll()
      runCommand(editor, "orderedList")
      assert.include(editor.getHTML(), "<ol>")
    })

    it("wraps bold as <strong> and italic as <em>", () => {
      editor.commands.setContent("<p>text</p>")
      editor.commands.selectAll()
      runCommand(editor, "bold")
      runCommand(editor, "italic")
      const html = editor.getHTML()
      assert.include(html, "<strong>")
      assert.include(html, "<em>")
    })

    it("adds a link with only an href attribute", () => {
      editor.commands.setContent("<p>text</p>")
      editor.commands.selectAll()
      assert.isTrue(applyLink(editor, "https://learn.mit.edu/c/x"))
      const html = editor.getHTML()
      assert.include(html, 'href="https://learn.mit.edu/c/x"')
    })

    it("refuses an unusable link target and leaves the document alone", () => {
      editor.commands.setContent("<p>text</p>")
      editor.commands.selectAll()
      assert.isFalse(applyLink(editor, "javascript:alert(1)"))
      assert.notInclude(editor.getHTML(), "javascript")
      assert.notInclude(editor.getHTML(), "<a")
    })

    it("removes a link with unlink", () => {
      editor.commands.setContent('<p><a href="https://x.mit.edu">text</a></p>')
      editor.commands.selectAll()
      runCommand(editor, "unlink")
      assert.notInclude(editor.getHTML(), "<a")
      assert.include(editor.getHTML(), "text")
    })

    it("keeps <u> and <blockquote>, which the allowlist advertises", () => {
      // ui/html.py allows both and the admin help text lists them. Without the
      // Underline/Blockquote extensions the schema would silently drop them the
      // next time any author opened the dialog and saved.
      editor.commands.setContent("<p><u>underlined</u> text</p>")
      assert.include(editor.getHTML(), "<u>underlined</u>")

      editor.commands.setContent("<blockquote><p>quoted</p></blockquote>")
      assert.include(editor.getHTML(), "<blockquote>")
      assert.include(editor.getHTML(), "quoted")
    })

    it("round-trips every tag the allowlist permits", () => {
      // The promise ui/html.py makes has to hold in both directions: what the
      // sanitizer keeps, the editor must not destroy.
      const samples = {
        p:          "<p>text</p>",
        strong:     "<p><strong>a</strong></p>",
        em:         "<p><em>a</em></p>",
        u:          "<p><u>a</u></p>",
        ul:         "<ul><li>a</li></ul>",
        ol:         "<ol><li>a</li></ol>",
        blockquote: "<blockquote><p>a</p></blockquote>",
        a:          '<p><a href="https://x.mit.edu">a</a></p>',
        br:         "<p>a<br>b</p>"
      }
      Object.keys(samples).forEach(tag => {
        editor.commands.setContent(samples[tag])
        assert.include(
          editor.getHTML(),
          `<${tag}`,
          `editor destroyed <${tag}>, which ui/html.py allows`
        )
      })
    })

    it("drops markup the allowlist does not cover when content is set", () => {
      // The schema itself is a filter: pasted markup outside the extension list
      // never enters the document, so it cannot be submitted.
      editor.commands.setContent(
        '<h2>heading</h2><p style="color:red">styled</p><script>alert(1)</script>'
      )
      const html = editor.getHTML()
      assert.notInclude(html, "<h2")
      assert.notInclude(html, "script")
      assert.notInclude(html, "style=")
      assert.include(html, "heading")
      assert.include(html, "styled")
    })

    it("returns false for an unknown command", () => {
      assert.isFalse(runCommand(editor, "nope"))
    })
  })
})
