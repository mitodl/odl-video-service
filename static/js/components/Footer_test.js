// @flow
/* global SETTINGS: false */
import React from "react"
import { render, screen } from "@testing-library/react"
import { assert } from "chai"

import Footer from "./Footer"

describe("Footer", () => {
  it("has 'Contact Us' link", () => {
    SETTINGS.support_email_address = "some@email.address"
    render(<Footer />)
    const link = screen.getByRole("link", { name: "Contact Us" })
    assert.equal(
      link.getAttribute("href"),
      `mailto:${SETTINGS.support_email_address}`
    )
  })

  it("has 'Accessibility' link", () => {
    render(<Footer />)
    const link = screen.getByRole("link", { name: "Accessibility" })
    assert.equal(link.getAttribute("href"), "https://accessibility.mit.edu/")
  })
})
