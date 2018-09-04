import React from "react"
import { assert } from "chai"
import { shallow } from "enzyme"
import sinon from "sinon"

import ProgressSlider from "./ProgressSlider"

describe("ProgressSlider", () => {
  let props, sandbox

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    props = {
      progress: 0.42
    }
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = extraProps => {
    return shallow(<ProgressSlider {...{ ...props, ...extraProps }} />)
  }

  it("renders progress bar with expected width", () => {
    const wrapper = renderComponent()
    const progressBar = wrapper.find(".progress")
    assert.equal(
      progressBar.props().style.width,
      `${100 * wrapper.props().value}%`
    )
  })

  it("clicking triggers onChange", () => {
    const onChangeSpy = sandbox.spy()
    const wrapper = renderComponent({
      onChange: onChangeSpy
    })
    const fakeBounds = { x: 10, width: 100 }
    const fakeEvent = { pageX: 42 }
    const getBoundsStub = sandbox.stub(wrapper.instance(), "getBounds")
    getBoundsStub.returns(fakeBounds)
    const expectedValue = (fakeEvent.pageX - fakeBounds.x) / fakeBounds.width
    wrapper.find(".time-slider").simulate("click", fakeEvent)
    sinon.assert.calledWith(onChangeSpy, expectedValue)
  })
})
