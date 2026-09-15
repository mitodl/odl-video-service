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

  it("leaves the title alone on unmount, neither restoring nor clearing it", () => {
    // A DELIBERATE divergence from react-document-title 2.0.3, not a
    // reproduction of it -- see the comment on DocumentTitle.js. That package
    // CLEARED document.title to "" once its last instance unmounted
    // (reducePropsToState returns undefined for an empty propsList, then
    // `title || ''`). It did not restore "before" either -- it kept no stack
    // -- so "before" is the outcome neither implementation ever produced, and
    // asserting against it is what distinguishes the two behaviours:
    //   package  -> ""
    //   this     -> "during"
    //   neither  -> "before"
    document.title = "before"
    const { unmount } = render(
      <DocumentTitle title="during">
        <div />
      </DocumentTitle>
    )
    assert.equal(document.title, "during")

    unmount()
    assert.equal(
      document.title,
      "during",
      'expected the last title to persist; "" would mean the package\'s ' +
        'clear-on-unmount got reintroduced, "before" a restore that neither ' +
        "implementation ever did"
    )
  })
})
