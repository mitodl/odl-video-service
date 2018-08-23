// @flow
/* global SETTINGS: false */
import React from "react"
import ErrorMessage from "./ErrorMessage"

export const UnableToLoadData = () => {
  const supportEmail: string = SETTINGS.support_email_address
  return (
    <ErrorMessage>
      <p>
        Sorry, we were unable to load the data necessary to process your
        request. Please reload the page.
      </p>
      {supportEmail ? (
        <p>
          If this happens again, please contact&nbsp;
          <a href={`mailto:${supportEmail}`}>{supportEmail}</a>.
        </p>
      ) : null}
    </ErrorMessage>
  )
}
