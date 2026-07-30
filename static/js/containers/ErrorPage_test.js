// @flow
/* global SETTINGS */
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { screen } from "@testing-library/react"
import configureTestStore from "redux-asserts"

import * as api from "../lib/api"
import ErrorPage from "./ErrorPage"
import { actions } from "../actions"
import rootReducer from "../reducers"
import { makeCollection } from "../factories/collection"
import renderWithProviders from "../testUtils/renderWithProviders"

describe("ErrorPage", () => {
  let sandbox, store, collections, listenForActions

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    collections = [makeCollection(), makeCollection(), makeCollection()]

    sandbox
      .stub(api, "getCollections")
      .returns(Promise.resolve({ results: collections }))
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderPage = async (props = {}) => {
    let result

    await listenForActions(
      [
        actions.collectionsList.get.requestType,
        actions.collectionsList.get.successType
      ],
      () => {
        result = renderWithProviders(<ErrorPage {...props} />, { store })
      }
    )
    return result
  }

  // eslint-disable-next-line no-unused-vars
  for (const [status, title, message] of [
    [
      403,
      "You do not have permission to view this video",
      "Please contact course faculty or staff and ask them to add you as a student or listener on stellar.mit.edu"
    ],
    [
      404,
      "Page not found",
      "This is a 404 error. This is not the page you were looking for. If you are looking for a video or collection, it is no longer available for viewing."
    ],
    [
      500,
      "Oops! Something went wrong...",
      "This is a 500 error. Something went wrong with the software." +
        " If this continues to happen please Contact Support."
    ]
  ]) {
    it(`renders an error for status=${status}`, async () => {
      SETTINGS.status_code = status
      const { container } = await renderPage()

      // The title is a single text node, so the accessible query works.
      assert.isNotNull(screen.getByText(title))

      // The message is deliberately not queried with getByText: for status
      // 500 the copy is split across a <span>, an <a>, and a trailing text
      // node, so no single element holds the whole string. textContent on
      // the container element is the documented RTL fallback for that case.
      const messageEl = container.querySelector(".error-page .message")
      assert.isNotNull(messageEl, "expected a .message element to render")
      assert.equal(messageEl.textContent.trim(), message)
    })
  }
})
