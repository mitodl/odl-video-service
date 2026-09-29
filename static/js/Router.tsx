import React from "react"
import { Provider } from "react-redux"
import type { Store } from "redux"
import { Route, Router as ReactRouter } from "react-router-dom"

import App from "./containers/App"
import withTracker from "./util/withTracker"

// AppRouter, not Router: React identifies a component by its class name, so a
// class of ours named `Router` would be indistinguishable from react-router's
// own `Router` -- which testUtils/suppressVendorLifecycleWarnings.tsx excuses
// deprecated-lifecycle warnings for. A deprecated lifecycle added here would
// then be silently swallowed instead of failing the run. The collision test in
// suppressVendorLifecycleWarnings_test.ts enforces this for every component.
/*
 * react-router 4 ships no type declarations, so `history` is declared by the
 * one member ReactRouter is handed it for rather than adding a types package.
 */
type Props = {
  history: unknown
  store: Store
  children?: React.ReactNode
}

export default class AppRouter extends React.Component<Props> {
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
