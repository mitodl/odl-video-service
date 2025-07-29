/* global Store, SETTINGS: false */
import React from "react"
import { Provider } from "react-redux"
import { BrowserRouter as ReactRouter } from "react-router-dom"
import ga from "react-ga"

import App from "./containers/App"

export default class Router extends React.Component {
  props: {
    store: Store
  }

  componentDidMount() {
    // Initialize Google Analytics
    const debug = SETTINGS.reactGaDebug === "true"
    if (SETTINGS.gaTrackingID) {
      ga.initialize(SETTINGS.gaTrackingID, { debug: debug })
    }
  }

  render() {
    const { children, store } = this.props

    return (
      <div>
        <Provider store={store}>
          <ReactRouter>{children}</ReactRouter>
        </Provider>
      </div>
    )
  }
}
export const routes = <App />
