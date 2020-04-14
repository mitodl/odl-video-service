import React from "react"
import { shallow } from "enzyme"
import { assert } from "chai"

import App from "./App"

describe("App", () => {
  const renderComponent = (extraProps = {}) => {
    const mergedProps = {
      match: {},
      ...extraProps
    }
    return shallow(<App {...mergedProps} />)
  }

  it("has toast message", () => {
    const wrapper = renderComponent()
    assert.isTrue(wrapper.find("Connect(ToastOverlay)").exists())
  })
})
