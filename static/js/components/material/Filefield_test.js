// @flow
import React from "react"
import { shallow } from "enzyme"
import { assert } from "chai"

import Filefield from "./Filefield"

describe("Filefield test", () => {
  const renderFilefield = (props = {}) => shallow(<Filefield {...props} />)

  it("should render a link, with appropriate classes", () => {
    const wrapper = renderFilefield()
    assert.deepEqual(wrapper.props().className, "button-link upload-link")
  })

  it("should add a class name to the upload link if provided", () => {
    const wrapper = renderFilefield({ className: "my-awesome-button" })
    assert.include(wrapper.props().className, "my-awesome-button ")
  })

  it("should accept certain file types", () => {
    const filetype = "video"
    const wrapper = renderFilefield({ accept: filetype })
    assert.equal(wrapper.find("input").props().accept, filetype)
  })

  it("should include a file input", () => {
    const wrapper = renderFilefield()
    assert.equal(wrapper.find("input").props().type, "file")
  })
})
