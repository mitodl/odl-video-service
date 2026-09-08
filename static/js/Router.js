/* global Store */
import React from "react"
import { Provider } from "react-redux"
import { Route, Router as ReactRouter } from "react-router-dom"

import App from "./containers/App"
import withTracker from "./util/withTracker"

// AppRouter, not Router: React identifies a component by its class name, so a
// class of ours named `Router` would be indistinguishable from react-router's
// own `Router` -- which testUtils/suppressVendorLifecycleWarnings.js excuses
// deprecated-lifecycle warnings for. A deprecated lifecycle added here would
// then be silently swallowed instead of failing the run. The collision test in
// suppressVendorLifecycleWarnings_test.js enforces this for every component.
export default class AppRouter extends React.Component {
  props: {
    history: Object,
    store: Store
  }

  render() {
    const { children, history, store } = this.props

    return (
      <div>
        <Provider store={store}>
          <ReactRouter history={history}>{children}</ReactRouter>
        </Provider>
      </div>
    )
  }
}
export const routes = <Route component={withTracker(App)} />
