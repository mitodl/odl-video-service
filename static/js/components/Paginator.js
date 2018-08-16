// @flow
/* global SETTINGS: false */
import React from "react"


class Paginator extends React.Component<*, void> {
  render () {
    const { currentPage, totalPages, style } = this.props
    const className = `paginator ${this.props.className || ''}`
    return (
      <div className={className} style={style}>
        <div className="contents" style={{position: "relative"}}>
          { this.renderPrevNextButton("prev") }
          <span className="paginator-spacer"/>
          <span className="paginator-current-range">
            <span className="paginator-current-page">{currentPage}</span>
            {" of "}
            <span className="paginator-total-pages">{totalPages}</span>
          </span>
          <span className="paginator-spacer"/>
          { this.renderPrevNextButton("next") }
        </div>
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
    let className = `paginator-button paginator-${nextPrevType}-button`
    let iconExtraClassNames = ""
    if (disabled) {
      className += ' disabled'
    } else {
      className += ' activated'
      iconExtraClassNames = "activated"
    }
    return (
      <span
        className={className}
        onClick={clickHandler}
        disabled={disabled}
      >
        <i className={`material-icons ${iconExtraClassNames}`}>{iconKey}</i>
      </span>
    )
  }

  noop () {}
}

export default Paginator
