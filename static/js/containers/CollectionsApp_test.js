import React from "react"
import { shallow } from "enzyme"
import { assert } from "chai"

import CollectionsApp from "./CollectionsApp"


describe("CollectionsApp", () => {
  const renderComponent = (extraProps = {}) => {
    const mergedProps = {
      match: {},
      ...extraProps,
    }
    return shallow(<CollectionsApp {...mergedProps}/>)
  }

  it("has toast message", () => {
    const wrapper = renderComponent()
    assert.isTrue(wrapper.find('Connect(ToastOverlay)').exists())
  })
})
