import React from "react"
import { assert } from "chai"
import { connect } from "react-redux"
import configureTestStore from "redux-asserts"

import rootReducer from "../reducers"
import renderWithProviders from "./renderWithProviders"

const ShowsStoreKeys = ({ keyCount }) => <div>keys:{keyCount}</div>

const Connected = connect(state => ({
  keyCount: Object.keys(state).length
}))(ShowsStoreKeys)

describe("renderWithProviders", () => {
  let store

  beforeEach(() => {
    store = configureTestStore(rootReducer)
  })

  it("renders a connected component with the store in context", () => {
    const { getByText } = renderWithProviders(<Connected />, { store })
    const expected = `keys:${Object.keys(store.getState()).length}`
    assert.isNotNull(getByText(expected))
  })

  it("echoes the store back on the result", () => {
    const result = renderWithProviders(<Connected />, { store })
    assert.strictEqual(result.store, store)
  })

  it("returns the standard RTL result object", () => {
    const result = renderWithProviders(<Connected />, { store })
    assert.isFunction(result.rerender)
    assert.isFunction(result.unmount)
    assert.instanceOf(result.container, window.HTMLElement)
  })

  it("throws a clear error when no store is given", () => {
    assert.throws(
      () => renderWithProviders(<Connected />),
      "renderWithProviders requires a `store` option"
    )
  })

  it("forwards unrecognised options to RTL render", () => {
    const host = document.createElement("div")
    document.body.appendChild(host)
    const { container } = renderWithProviders(<Connected />, {
      store,
      container: host
    })
    assert.strictEqual(container, host)
  })
})
