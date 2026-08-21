// @flow
import React from "react"
import { render } from "@testing-library/react"
import { assert } from "chai"

import Filefield from "./Filefield"

describe("Filefield test", () => {
  const renderFilefield = (props = {}) => render(<Filefield {...props} />)

  it("should render a link, with appropriate classes", () => {
    const { container } = renderFilefield()
    assert.deepEqual(container.firstChild.className, "button-link upload-link")
  })

  it("should add a class name to the upload link if provided", () => {
    const { container } = renderFilefield({ className: "my-awesome-button" })
    assert.include(container.firstChild.className, "my-awesome-button ")
  })

  it("should accept certain file types", () => {
    const filetype = "video"
    const { container } = renderFilefield({ accept: filetype })
    assert.equal(container.querySelector("input").accept, filetype)
  })

  it("should include a file input", () => {
    const { container } = renderFilefield()
    assert.equal(container.querySelector("input").type, "file")
  })
})
