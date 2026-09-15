// @flow
import React from "react"
import { render } from "@testing-library/react"
import { assert } from "chai"

import Description from "./Description"
import {
  DESCRIPTION_FORMAT_HTML,
  DESCRIPTION_FORMAT_TEXT
} from "../../constants"

/*
 * The point of this component is that the two formats do NOT share a render
 * path, so every test here is about the difference between them.
 */
describe("Description", () => {
  const renderDescription = (props = {}) =>
    render(
      <Description
        description=""
        descriptionFormat={DESCRIPTION_FORMAT_TEXT}
        {...props}
      />
    )

  it("renders rich text as markup", () => {
    const { container } = renderDescription({
      description:       '<p>see the <a href="https://mit.edu">notes</a></p>',
      descriptionFormat: DESCRIPTION_FORMAT_HTML
    })
    assert.lengthOf(container.querySelectorAll("a"), 1)
    assert.equal(
      container.querySelector("a").getAttribute("href"),
      "https://mit.edu"
    )
  })

  it("renders plain text as text, so a tag stays visible instead of applying", () => {
    const { container } = renderDescription({
      description:       "<b>bold?</b>",
      descriptionFormat: DESCRIPTION_FORMAT_TEXT
    })
    assert.lengthOf(container.querySelectorAll("b"), 0)
    assert.equal(container.textContent, "<b>bold?</b>")
  })

  it("keeps every word of plain text that HTML would have swallowed", () => {
    /*
     * The failure this exists to prevent: injected as markup, `<b to a` opens an
     * unterminated tag and the browser drops the rest of the description. On the
     * page that looks like the text simply vanished.
     */
    const description = "Compare <b to a. See the notes. Q&A after."
    const { container } = renderDescription({
      description,
      descriptionFormat: DESCRIPTION_FORMAT_TEXT
    })
    assert.equal(container.textContent, description)
  })

  it("marks plain text for pre-wrap, which is what keeps its line breaks", () => {
    const { container } = renderDescription({
      description:       "one\ntwo",
      descriptionFormat: DESCRIPTION_FORMAT_TEXT,
      className:         "description"
    })
    const node = container.querySelector(".description")
    assert.isTrue(node.classList.contains("description-plain-text"))
    assert.equal(node.textContent, "one\ntwo")
  })

  it("does not mark rich text for pre-wrap", () => {
    const { container } = renderDescription({
      description:       "<p>one</p>",
      descriptionFormat: DESCRIPTION_FORMAT_HTML,
      className:         "description"
    })
    assert.isFalse(
      container
        .querySelector(".description")
        .classList.contains("description-plain-text")
    )
  })

  it("treats an unknown or missing format as plain text", () => {
    // The safe direction: markup shown as text is ugly, text shown as markup
    // loses content and can carry a handler.
    const { container } = renderDescription({
      description:       "<b>x</b>",
      descriptionFormat: undefined
    })
    assert.lengthOf(container.querySelectorAll("b"), 0)
  })

  it("renders nothing when there is no description", () => {
    for (const description of ["", null, undefined]) {
      const { container } = renderDescription({ description })
      // React 15 renders null as a comment node, so assert on elements and
      // text rather than on innerHTML.
      assert.lengthOf(container.querySelectorAll("*"), 0)
      assert.equal(container.textContent, "")
    }
  })

  it("keeps the className it is given", () => {
    const { container } = renderDescription({
      description:       "<p>x</p>",
      descriptionFormat: DESCRIPTION_FORMAT_HTML,
      className:         "video-description mdc-typography--body1"
    })
    assert.isNotNull(container.querySelector(".video-description"))
  })
})
