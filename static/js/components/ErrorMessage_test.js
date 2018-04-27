// @flow
import React from "react"
import { shallow } from "enzyme"
import { assert } from "chai"

import ErrorMessage from "./ErrorMessage"

describe("ErrorMessage", () => {
  const renderComponent = (extraProps = {}) => {
    return shallow(<ErrorMessage {...extraProps}/>)
  }

  it("has odl-error-message className", () => {
    const wrapper = renderComponent({
      className: "some-class"
    })
    assert.equal(
      wrapper.get(0).props.className,
      "odl-error-message some-class"
    )
  })

  it("renders children", () => {
    const wrapper = renderComponent({
      children: [
        (<div key="a" className="a">a</div>),
        (<div key="b" className="b">b</div>)
      ]
    })
    assert.isTrue(wrapper.find('.a').exists())
    assert.isTrue(wrapper.find('.b').exists())
  })
})
