// @flow
/* global SETTINGS: false */
import React from "react"

import Button from "./material/Button"


class Paginator extends React.Component<*, void> {
  render () {
    const { currentPage, totalPages } = this.props
    return (
      <div className="paginator">
        <span className="paginator-current-range">
          Page {currentPage} of {totalPages}
        </span>
      
        <span className="paginator-buttons"
          style={{
            marginLeft: '.5em',
            position: 'relative',
            top: '-.1em',
          }}
        >
          { this.renderPrevNextButton("prev") }
          { this.renderPrevNextButton("next") }
        </span>
      </div>
    )
  }

  renderPrevNextButton (nextPrevType: string) {
    const { currentPage, totalPages, onClickPrev, onClickNext } = this.props
    let iconKey
    let disabled = true
    let clickHandler = this.noop
    if (nextPrevType === 'next') {
      iconKey = 'chevron_right'
      if (currentPage < totalPages) {
        clickHandler = onClickNext
        disabled = false
      }
    } else if (nextPrevType === 'prev') {
      iconKey = 'chevron_left'
      if (currentPage > 1) {
        clickHandler = onClickPrev
        disabled = false
      }
    }
    const buttonStyle = {
      margin: 0,
      minWidth: 0,
      padding: 0,
      height: '24px',
      lineHeight: '24px',
    }
    const mdcClassNames = 'mdc-button mdc-button--dense mdc-button--stroked'
    /*
    return (
      <button
        className={`${mdcClassNames} paginator-${nextPrevType}-button`}
        style={buttonStyle}
        onClick={clickHandler}
        disabled={disabled}
      >
        <i
          className="material-icons mdc-button__icon"
          style={{top: 0, verticalAlign: 'top'}}
        >
          {iconKey}
        </i>
      </button>
    )
    */
    let className = `paginator-button paginator-${nextPrevType}-button`
    if (disabled) {
      className += ' disabled'
    }
    return (
      <span
        className={className}
        onClick={clickHandler}
        disabled={disabled}
      >
        <i className="material-icons">{iconKey}</i>
      </span>
    )
  }

  noop () {}
}

export default Paginator
