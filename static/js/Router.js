/* global Store */
import React from "react"
import { Provider } from "react-redux"
import { Route, Router as ReactRouter } from "react-router-dom"

import App from "./containers/App"
import withTracker from "./util/withTracker"

export default class Router extends React.Component {
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
