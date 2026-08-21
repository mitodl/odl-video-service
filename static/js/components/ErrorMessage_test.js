// @flow
import React from "react"
import { render } from "@testing-library/react"
import { assert } from "chai"

import ErrorMessage from "./ErrorMessage"

describe("ErrorMessage", () => {
  const renderComponent = (extraProps = {}) => {
    return render(<ErrorMessage {...extraProps} />)
  }

  it("has odl-error-message className", () => {
    const { container } = renderComponent({
      className: "some-class"
    })
    assert.equal(container.firstChild.className, "odl-error-message some-class")
  })

  it("renders children", () => {
    const { container } = renderComponent({
      children: [
        <div key="a" className="a">
          a
        </div>,
        <div key="b" className="b">
          b
        </div>
      ]
    })
    assert.isNotNull(container.querySelector(".a"))
    assert.isNotNull(container.querySelector(".b"))
  })
})
