import React from "react"
import { assert } from "chai"
import { render } from "@testing-library/react"

import DocumentTitle from "./DocumentTitle"

describe("DocumentTitle", () => {
  let original

  beforeEach(() => {
    original = document.title
  })

  afterEach(() => {
    document.title = original
  })

  it("sets document.title on mount", () => {
    render(
      <DocumentTitle title="OVS | a title">
        <div className="child" />
      </DocumentTitle>
    )
    assert.equal(document.title, "OVS | a title")
  })

  it("renders its children unchanged", () => {
    const { container } = render(
      <DocumentTitle title="whatever">
        <div className="child">hello</div>
      </DocumentTitle>
    )
    const child = container.querySelector(".child")
    assert.isNotNull(child)
    assert.equal(child.textContent, "hello")
  })

  it("updates document.title when the prop changes", () => {
    const { rerender } = render(
      <DocumentTitle title="first">
        <div />
      </DocumentTitle>
    )
    assert.equal(document.title, "first")

    rerender(
      <DocumentTitle title="second">
        <div />
      </DocumentTitle>
    )
    assert.equal(document.title, "second")
  })

  it("does not restore the previous title on unmount", () => {
    // Deliberate: react-document-title did not restore either, and OVS relies
    // on the title persisting until the next page sets its own. Restoring here
    // would be a behaviour change disguised as a dependency swap.
    document.title = "before"
    const { unmount } = render(
      <DocumentTitle title="during">
        <div />
      </DocumentTitle>
    )
    assert.equal(document.title, "during")

    unmount()
    assert.equal(document.title, "during")
  })
})
