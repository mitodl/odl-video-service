// @flow
import React from "react"
import sinon from "sinon"
import { render, fireEvent, waitFor } from "@testing-library/react"
import { assert } from "chai"

import RichTextEditor from "./RichTextEditor"

/*
 * RTL rather than Enzyme, deliberately: the migration ledger
 * (scripts/test/ledger.sh) ratchets the Enzyme file count down, and a new
 * Enzyme file would move it the wrong way.
 *
 * Consequence for this file: there is no component instance to poke. Everything
 * is asserted through the DOM, including the editor's own content - TipTap keeps
 * the document in a contenteditable element, so `.ProseMirror` innerHTML is the
 * real output rather than a proxy for it.
 */
describe("RichTextEditor", () => {
  let onChange

  const renderEditor = (props = {}) =>
    render(
      <RichTextEditor
        label="Description"
        id="test-desc"
        value=""
        onChange={onChange}
        {...props}
      />
    )

  // The editor engine is a split chunk, so it arrives a microtask after mount.
  const waitForEditor = async (container: HTMLElement) =>
    waitFor(() => {
      assert.isOk(
        container.querySelector(".ProseMirror"),
        "editor never mounted"
      )
    })

  const toolbarButton = (container: HTMLElement, label: string) => {
    const button = container.querySelector(`button[aria-label="${label}"]`)
    assert.isOk(button, `no toolbar button labelled ${label}`)
    return button
  }

  const editorHtml = (container: HTMLElement) => {
    const el = container.querySelector(".ProseMirror")
    return el ? el.innerHTML : ""
  }

  /*
   * Note on the split of responsibility. ProseMirror reads the *browser*
   * selection, and jsdom does not drive its selection observer, so a command
   * that needs a text range (bold, applying a link across a selection) cannot
   * be exercised from here without reaching for the component instance. Those
   * semantics are covered against a live editor in static/js/lib/editor_test.js
   * instead; this file covers the wiring - the controls exist, are labelled, and
   * are connected to the editor and to onChange.
   */

  beforeEach(() => {
    onChange = sinon.stub()
  })

  it("names the editable region with the label", async () => {
    const { container } = renderEditor()
    await waitForEditor(container)
    assert.equal(container.querySelector("label").textContent, "Description")
    // A contenteditable div is not a labelable element, so htmlFor cannot bind
    // to it - aria-labelledby is what gives the field its accessible name.
    assert.equal(
      container.querySelector("#test-desc").getAttribute("aria-labelledby"),
      "test-desc-label"
    )
  })

  it("shows the value as markup before the editor chunk arrives", () => {
    // Rendered synchronously, before the dynamic import resolves: the field must
    // not look empty while the chunk is in flight.
    const { container } = renderEditor({
      value: "<p>existing <strong>text</strong></p>"
    })
    assert.include(container.innerHTML, "existing <strong>text</strong>")
  })

  it("renders the toolbar as a toolbar once loaded", async () => {
    const { container } = renderEditor()
    await waitForEditor(container)
    const toolbar = container.querySelector(".rte-toolbar")
    assert.equal(toolbar.getAttribute("role"), "toolbar")
    assert.lengthOf(container.querySelectorAll("button.rte-button"), 6)
  })

  it("labels every control and renders it as a Material Icon", async () => {
    const { container } = renderEditor()
    await waitForEditor(container)
    const labels = [...container.querySelectorAll("button.rte-button")].map(b =>
      b.getAttribute("aria-label")
    )
    assert.deepEqual(labels, [
      "Bold",
      "Italic",
      "Bulleted list",
      "Numbered list",
      "Add link",
      "Remove link"
    ])
    const bold = toolbarButton(container, "Bold")
    const glyph = bold.querySelector("i.material-icons")
    assert.isOk(glyph)
    assert.equal(glyph.textContent, "format_bold")
  })

  it("loads the current value into the editor", async () => {
    const { container } = renderEditor({ value: "<p>hello</p>" })
    await waitForEditor(container)
    assert.include(editorHtml(container), "hello")
  })

  it("reports edits to onChange as HTML", async () => {
    const { container } = renderEditor({ value: "<p>before</p>" })
    await waitForEditor(container)
    fireEvent.click(toolbarButton(container, "Bulleted list"))
    await waitFor(() => {
      sinon.assert.called(onChange)
    })
    assert.include(onChange.lastCall.args[0], "<ul>")
  })

  it("applies a bulleted list, not an attributed ordered list", async () => {
    const { container } = renderEditor({ value: "<p>item</p>" })
    await waitForEditor(container)
    fireEvent.click(toolbarButton(container, "Bulleted list"))
    await waitFor(() => {
      assert.include(editorHtml(container), "<ul")
    })
    assert.notInclude(editorHtml(container), "data-list")
  })

  it("opens an inline link field rather than a browser prompt", async () => {
    const { container } = renderEditor({ value: "<p>text</p>" })
    await waitForEditor(container)
    assert.lengthOf(container.querySelectorAll("input.rte-link-input"), 0)
    fireEvent.click(toolbarButton(container, "Add link"))
    assert.lengthOf(container.querySelectorAll("input.rte-link-input"), 1)
  })

  it("accepts a usable link target and closes the field", async () => {
    const { container } = renderEditor({ value: "<p>text</p>" })
    await waitForEditor(container)
    fireEvent.click(toolbarButton(container, "Add link"))
    fireEvent.change(container.querySelector("input.rte-link-input"), {
      target: { value: "learn.mit.edu/c/x" }
    })
    fireEvent.click(
      [...container.querySelectorAll("button.rte-button")].find(
        b => b.textContent === "Apply"
      )
    )
    await waitFor(() => {
      assert.lengthOf(container.querySelectorAll("input.rte-link-input"), 0)
    })
    assert.lengthOf(container.querySelectorAll(".rte-link-error"), 0)
  })

  it("keeps the field open and explains an unusable link", async () => {
    const { container } = renderEditor({ value: "<p>text</p>" })
    await waitForEditor(container)
    fireEvent.click(toolbarButton(container, "Add link"))
    fireEvent.change(container.querySelector("input.rte-link-input"), {
      target: { value: "javascript:alert(1)" }
    })
    fireEvent.click(
      [...container.querySelectorAll("button.rte-button")].find(
        b => b.textContent === "Apply"
      )
    )
    await waitFor(() => {
      assert.lengthOf(container.querySelectorAll(".rte-link-error"), 1)
    })
    assert.lengthOf(container.querySelectorAll("input.rte-link-input"), 1)
    assert.notInclude(editorHtml(container), "javascript")
  })

  it("pushes an externally changed value into the editor", async () => {
    const { container, rerender } = renderEditor({ value: "<p>first</p>" })
    await waitForEditor(container)
    rerender(
      <RichTextEditor
        label="Description"
        id="test-desc"
        value="<p>second</p>"
        onChange={onChange}
      />
    )
    await waitFor(() => {
      assert.include(editorHtml(container), "second")
    })
    assert.notInclude(editorHtml(container), "first")
  })

  it("does not re-emit when the value it just produced comes back", async () => {
    // Writing the editor's own output back in would move the author's cursor to
    // the top of the field on every keystroke.
    const { container, rerender } = renderEditor({ value: "<p>first</p>" })
    await waitForEditor(container)
    const before = editorHtml(container)
    onChange.resetHistory()
    rerender(
      <RichTextEditor
        label="Description"
        id="test-desc"
        value="<p>first</p>"
        onChange={onChange}
      />
    )
    assert.equal(editorHtml(container), before)
    sinon.assert.notCalled(onChange)
  })

  it("shows a placeholder only while empty", async () => {
    const { container, rerender } = renderEditor({
      value:       "",
      placeholder: "Add a description"
    })
    await waitForEditor(container)
    assert.lengthOf(container.querySelectorAll(".rte-placeholder"), 1)
    rerender(
      <RichTextEditor
        label="Description"
        id="test-desc"
        value="<p>now filled</p>"
        placeholder="Add a description"
        onChange={onChange}
      />
    )
    assert.lengthOf(container.querySelectorAll(".rte-placeholder"), 0)
  })
})
