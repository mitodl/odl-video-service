// @flow
/* global SETTINGS */
import React from "react"
import sinon from "sinon"
import { mount } from "enzyme"
import { assert } from "chai"
import configureTestStore from "redux-asserts"
import { Provider } from "react-redux"

import * as api from "../lib/api"
import ErrorPage from "./ErrorPage"
import { actions } from "../actions"
import rootReducer from "../reducers"
import { makeCollection } from "../factories/collection"

describe("ErrorPage", () => {
  let sandbox, store, collections, listenForActions

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
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
    let wrapper

    await listenForActions(
      [
        actions.collectionsList.get.requestType,
        actions.collectionsList.get.successType
      ],
      () => {
        wrapper = mount(
          <Provider store={store}>
            <ErrorPage {...props} />
          </Provider>
        )
      }
    )
    if (!wrapper) throw new Error("Never will happen, make flow happy")
    return wrapper
  }

  for (const [status, title, message] of [
    [
      403,
      "You do not have permission to view this video",
      "If you want permission to view this video please Contact ODL Video Services."
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
      const wrapper = await renderPage()
      assert.equal(
        wrapper
          .find(".error-page .title")
          .text()
          .trim(),
        title
      )
      assert.equal(
        wrapper
          .find(".error-page .message")
          .text()
          .trim(),
        message
      )
    })
  }
})
