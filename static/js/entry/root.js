// @flow
/* global SETTINGS:false */
__webpack_public_path__ = SETTINGS.public_path // eslint-disable-line no-undef, camelcase
import React from "react"
import { createRoot } from "react-dom/client"
import { createBrowserHistory } from "history"

import configureStore from "../store/configureStore"
import AppRouter, { routes } from "../Router"

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

// Created once, outside renderApp: createRoot must be called at most once per
// container. renderApp runs again on every hot reload, so creating the root
// inside it would throw on the second call and break HMR.
const root = createRoot(rootEl)

const renderApp = Component => {
  root.render(
    <Component store={store} history={history}>
      {routes}
    </Component>
  )
}

renderApp(AppRouter)

if (module.hot) {
  module.hot.accept("../Router", () => {
    const AppRouterNext = require("../Router").default
    renderApp(AppRouterNext)
  })
}
