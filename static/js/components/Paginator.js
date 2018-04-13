// @flow
/* global SETTINGS: false */
import React from "react"

import Button from "./material/Button"


class Paginator extends React.Component<*, void> {
  render () {
    return (
      <div className="paginator">
        <span className="paginator-current-range">
          50 - 60 of 103
        </span>
      
        <span className="paginator-buttons">
          { this.renderPrevNextButton("prev") }
          { this.renderPrevNextButton("next") }
        </span>
      </div>
    )
  }

  renderPrevNextButton (nextPrevType: string) {
    let iconKey, clickHandler
    if (nextPrevType === 'next') {
      iconKey = 'chevron_right'
      clickHandler = this.props.onClickNext
    } else if (nextPrevType === 'prev') {
      iconKey = 'chevron_left'
      clickHandler = this.props.onClickPrev
    }
    const buttonStyle = {
      margin: 0,
      minWidth: 0,
      padding: 0,
    }
    return (
      <button
        className={`mdc-button paginator-${nextPrevType}-button`}
        style={buttonStyle}
        onClick={clickHandler}
      >
        <i
          className="material-icons mdc-button__icon"
          style={{top: 0, verticalAlign: 'top'}}
        >
          {iconKey}
        </i>
      </button>
    )
  }
}

export default Paginator
