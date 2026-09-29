// From https://github.com/ReactTraining/react-router/issues/4278#issuecomment-299692502
import React from "react"
import ga from "react-ga"

type TrackerProps = {
  location: {
    pathname: string
  }
}

const withTracker = <P extends TrackerProps>(
  WrappedComponent: React.ComponentType<P>
) => {
  const debug = SETTINGS.reactGaDebug === "true"

  if (SETTINGS.gaTrackingID) {
    ga.initialize(SETTINGS.gaTrackingID, { debug: debug })
  }

  const HOC = (props: P) => {
    const page = props.location.pathname
    ga.pageview(page)
    return <WrappedComponent {...props} />
  }

  return HOC
}

export default withTracker
