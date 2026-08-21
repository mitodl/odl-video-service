// @flow
import React from "react"
import { assert } from "chai"
import { MemoryRouter } from "react-router"
import configureTestStore from "redux-asserts"

import App from "./App"
import rootReducer from "../reducers"
import renderWithProviders from "../testUtils/renderWithProviders"

describe("App", () => {
  const renderComponent = (extraProps = {}) => {
    const mergedProps = {
      match: { url: "/" },
      ...extraProps
    }
    const store = configureTestStore(rootReducer, {
      toast: { messages: [{ key: "1", content: "test message" }] }
    })
    return renderWithProviders(
      <MemoryRouter>
        <App {...mergedProps} />
      </MemoryRouter>,
      { store }
    )
  }

  it("has toast message", () => {
    const { container } = renderComponent()
    assert.isNotNull(container.querySelector(".toast-overlay"))
  })
})
