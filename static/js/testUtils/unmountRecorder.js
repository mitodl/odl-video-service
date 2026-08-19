// @flow
import React from "react"

// Shared by harness_test.js and teardown_test.js, both of which need to
// observe when a mounted tree's componentWillUnmount fires. Each call
// returns an isolated component + counter so tests can't leak state into
// one another.
export const makeUnmountRecorder = () => {
  let unmountCount = 0

  class UnmountRecorder extends React.Component<*, void> {
    componentWillUnmount() {
      unmountCount += 1
    }

    render() {
      return <div>mounted</div>
    }
  }

  return { UnmountRecorder, getUnmountCount: () => unmountCount }
}
