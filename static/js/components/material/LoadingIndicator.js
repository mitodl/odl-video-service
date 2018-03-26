import React from "react"

import { LinearProgress } from "rmwc/LinearProgress"

export default class LoadingIndicator extends React.Component {
  render() {
    return (
      <div className="loading-indicator">
        <label>Loading...</label>
        <LinearProgress determinate={false} />
      </div>
    )
  }
}
