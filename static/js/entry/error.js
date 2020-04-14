// @flow
/* global SETTINGS:false */
__webpack_public_path__ = SETTINGS.public_path // eslint-disable-line no-undef, camelcase
import "react-hot-loader/patch"
import React from "react"
import ReactDOM from "react-dom"
import { Provider } from "react-redux"

import ErrorPage from "../containers/ErrorPage"
import configureStore from "../store/configureStore"

import * as Sentry from "@sentry/browser"

Sentry.init({
  dsn:         SETTINGS.sentry_dsn,
  release:     SETTINGS.release_version,
  environment: SETTINGS.environment
})

// Object.entries polyfill
import entries from "object.entries"
if (!Object.entries) {
  entries.shim()
}

const store = configureStore()

const rootEl = document.getElementById("container")

if (!rootEl) {
  throw new Error("Unable to find element 'container'")
}

ReactDOM.render(
  <Provider store={store}>
    <ErrorPage />
  </Provider>,
  rootEl
)
