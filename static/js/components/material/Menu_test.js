// @flow
import React from "react"
import { mount } from "enzyme"
import { assert } from "chai"
import sinon from "sinon"

import Menu from "./Menu"

describe("Menu", () => {
  const menuItems = [{ label: "Item 1", action: () => {} }]

  const renderMenu = (props = {}) =>
    mount(
      <Menu
        open={false}
        showMenu={sinon.stub()}
        closeMenu={sinon.stub()}
        menuItems={menuItems}
        {...props}
      />
    )

  // componentDidUpdate replaced componentWillReceiveProps here. Nothing
  // previously mounted this component and toggled `open`, so a regression
  // in that comparison (e.g. the mdc menu open state getting out of sync
  // after a reopen) would still pass the existing shallow-rendered
  // VideoCard tests.
  it("tracks the open prop on the underlying MDC menu across toggles, including a reopen", () => {
    const wrapper = renderMenu({ open: false })
    const instance = wrapper.instance()
    assert.isFalse(instance.menu.open)

    wrapper.setProps({ open: true })
    assert.isTrue(instance.menu.open)

    wrapper.setProps({ open: false })
    assert.isFalse(instance.menu.open)

    wrapper.setProps({ open: true })
    assert.isTrue(instance.menu.open)
  })

  it("does not touch the MDC menu when an unrelated prop changes", () => {
    const wrapper = renderMenu({ open: false })
    const instance = wrapper.instance()
    const menu = instance.menu

    wrapper.setProps({ menuItems: [{ label: "Item 2", action: () => {} }] })
    assert.strictEqual(instance.menu, menu)
    assert.isFalse(instance.menu.open)
  })
})
