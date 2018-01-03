// @flow
import React from "react"
import { shallow } from "enzyme"
import { assert } from "chai"

import Button from "./Button"

describe("Button test", () => {
  const renderButton = (props = {}) => shallow(<Button {...props} />)

  it("should render a button, with appropriate classes", () => {
    const wrapper = renderButton()
    assert.deepEqual(wrapper.props().className, "mdc-button")
  })

  it("should stick a className on, if provided", () => {
    const wrapper = renderButton({ className: "my-awesome-button" })
    assert.include(wrapper.props().className, "my-awesome-button")
  })

  it("should splat in other props", () => {
    const awesomeCallback = () => "function!"
    const wrapper = renderButton({ onClick: awesomeCallback })
    assert.equal(wrapper.props().onClick, awesomeCallback)
  })

  it("should render children", () => {
    const wrapper = shallow(
      <Button>
        <div>HEY THERE!</div>
      </Button>
    )
    assert.equal(wrapper.text(), "HEY THERE!")
    assert.lengthOf(wrapper.find("div"), 1)
  })
})
