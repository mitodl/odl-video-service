// @flow
/* global SETTINGS: false */
import React from "react"
import { shallow } from "enzyme"
import { assert } from "chai"

import Footer from "./Footer"

describe("Footer", () => {
  const renderComponent = (props = {}) => {
    return shallow(<Footer {...props} />)
  }
  it("has 'Contact Us' link", () => {
    SETTINGS.support_email_address = "some@email.address"
    const wrapper = renderComponent()
    const link = wrapper.find("a.contact-us")
    assert.equal(link.text(), "Contact Us")
    assert.equal(link.prop("href"), `mailto:${SETTINGS.support_email_address}`)
  })
  it("has 'Accessibility' link", () => {
    const wrapper = renderComponent()
    const link = wrapper.find("a.accessibility")
    assert.equal(link.text(), "Accessibility")
    assert.equal(link.prop("href"), "https://accessibility.mit.edu/")
  })
})
