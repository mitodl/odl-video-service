// @flow
/* global SETTINGS: false */
import React from "react"

import WithDrawer from "./WithDrawer"

export default class ErrorPage extends React.Component<*, void> {
  errorTitle = () => {
    switch (SETTINGS.status_code) {
    case 403:
      return "You do not have permission to view this video"
    case 404:
      return "Page not found"
    default:
      return "Oops! Something went wrong..."
    }
  }

  errorMessage = () => {
    switch (SETTINGS.status_code) {
    case 403:
      return (
        <span>
            If you want permission to view this video please{" "}
          <a href={`mailto:${SETTINGS.support_email_address}`}>
              Contact ODL Video Services
          </a>.
        </span>
      )
    case 404:
      return (
        <span>
            This is a 404 error. This is not the page you were looking for. If
            you are looking for a video or collection, it is no longer available
            for viewing.
        </span>
      )
    default:
      return (
        <span>
            This is a 500 error. Something went wrong with the software. If this
            continues to happen please{" "}
          <a href={`mailto:${SETTINGS.support_email_address}`}>
              Contact Support
          </a>.
        </span>
      )
    }
  }

  render() {
    return (
      <WithDrawer>
        <div className="error-page">
          <div className="content">
            <span className="title">{this.errorTitle()}</span>
            <p className="message">{this.errorMessage()}</p>
          </div>
        </div>
      </WithDrawer>
    )
  }
}
