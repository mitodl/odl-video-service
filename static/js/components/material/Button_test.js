// @flow
import React from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import { assert } from "chai"
import sinon from "sinon"

import Button from "./Button"

describe("Button test", () => {
  const renderButton = (props = {}) => render(<Button {...props} />)

  it("should render a button, with appropriate classes", () => {
    const { container } = renderButton()
    assert.deepEqual(container.firstChild.className, "mdc-button")
  })

  it("should stick a className on, if provided", () => {
    const { container } = renderButton({ className: "my-awesome-button" })
    assert.include(container.firstChild.className, "my-awesome-button")
  })

  it("should invoke a passed-through onClick handler when clicked", () => {
    const onClick = sinon.spy()
    renderButton({ onClick })
    fireEvent.click(screen.getByRole("button"))
    assert.isTrue(onClick.called)
  })

  it("should render children", () => {
    render(
      <Button>
        <div>HEY THERE!</div>
      </Button>
    )
    assert.exists(screen.getByText("HEY THERE!"))
  })
})
