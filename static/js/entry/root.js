// @flow
/* global SETTINGS:false */
__webpack_public_path__ = SETTINGS.public_path // eslint-disable-line no-undef, camelcase
import "react-hot-loader/patch"
import React from "react"
import ReactDOM from "react-dom"
import { AppContainer } from "react-hot-loader"
import { createBrowserHistory } from "history"

import configureStore from "../store/configureStore"
import Router, { routes } from "../Router"

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

const history = createBrowserHistory()
const renderApp = Component => {
  ReactDOM.render(
    <AppContainer>
      <Component store={store} history={history}>
        {routes}
      </Component>
    </AppContainer>,
    rootEl
  )
}

renderApp(Router)

if (module.hot) {
  module.hot.accept("../Router", () => {
    const RouterNext = require("../Router").default
    renderApp(RouterNext)
  })
}
