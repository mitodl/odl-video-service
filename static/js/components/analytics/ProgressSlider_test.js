import React from "react"
import { assert } from "chai"
import { render, fireEvent } from "@testing-library/react"
import sinon from "sinon"

import ProgressSlider from "./ProgressSlider"

describe("ProgressSlider", () => {
  let props, sandbox

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    // The real prop name is `value` (ProgressSlider destructures `value`,
    // not `progress` -- see ProgressSlider.js's render()). The old fixture
    // used `progress`, which the component never reads at all: both sides
    // of the old assertion degenerated to the string "NaN%", so it passed
    // for the wrong reason and could not catch a real regression in the
    // width calculation. Fixed here to the real prop name.
    props = {
      value: 0.42
    }
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = extraProps => {
    return render(<ProgressSlider {...{ ...props, ...extraProps }} />)
  }

  it("renders progress bar with expected width", () => {
    const { container } = renderComponent()
    const progressBar = container.querySelector(".progress")
    assert.equal(progressBar.style.width, `${props.value * 100}%`)
  })

  it("clicking triggers onChange", () => {
    const onChangeSpy = sandbox.spy()
    // getBounds() resolves to this.rootRef.getBoundingClientRect(), which
    // jsdom always returns as an all-zero rect -- stub the prototype (RTL
    // gives no instance handle) so onClickSlider computes against a fixed,
    // non-zero rect.
    const fakeBounds = { x: 10, width: 100 }
    sandbox.stub(ProgressSlider.prototype, "getBounds").returns(fakeBounds)
    const { container } = renderComponent({ onChange: onChangeSpy })
    // The component reads event.pageX, but jsdom's MouseEvent.pageX is a
    // read-only getter that returns clientX and ignores a pageX field in
    // MouseEventInit -- fireEvent's click init must carry clientX, not
    // pageX, or event.pageX resolves to 0 regardless of what's passed here.
    const clientX = 42
    const expectedValue = (clientX - fakeBounds.x) / fakeBounds.width
    fireEvent.click(container.querySelector(".time-slider"), { clientX })
    sinon.assert.calledWith(onChangeSpy, expectedValue)
  })
})
