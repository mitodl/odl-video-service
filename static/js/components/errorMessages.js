// @flow
/* global SETTINGS: false */
import React from "react"
import ErrorMessage from "./ErrorMessage"


export const UnableToLoadData = () => {
  // $FlowFixMe
  const supportEmail:string = SETTINGS.supportEmail
  return (
    <ErrorMessage>
      <p>Sorry, we were unable to load the data necessary to process your request. Please reload the page.</p>
      {
        supportEmail ? (
          <p>If this happens again, please contact&nbsp;
            <a href={`mailto:${supportEmail}`}>{supportEmail}</a>.
          </p>
        ) : null
      }
    </ErrorMessage>
  )
}
