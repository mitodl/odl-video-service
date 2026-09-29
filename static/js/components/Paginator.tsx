import React from "react"

type Props = {
  currentPage: number
  totalPages: number
  onClickNext: () => void
  onClickPrev: () => void
}

class Paginator extends React.Component<Props> {
  render() {
    const { currentPage, totalPages } = this.props
    return (
      <div className="paginator">
        <div className="contents" style={{ position: "relative" }}>
          {this.renderPrevNextButton("prev")}
          <span className="paginator-spacer" />
          <span className="paginator-current-range">
            <span className="paginator-current-page">{currentPage}</span>
            {" of "}
            <span className="paginator-total-pages">{totalPages}</span>
          </span>
          <span className="paginator-spacer" />
          {this.renderPrevNextButton("next")}
        </div>
      </div>
    )
  }

  renderPrevNextButton(nextPrevType: string) {
    const { currentPage, totalPages, onClickPrev, onClickNext } = this.props
    let iconKey: string | undefined
    let disabled = true
    let clickHandler = this.noop
    if (nextPrevType === "next") {
      iconKey = "chevron_right"
      if (currentPage < totalPages) {
        clickHandler = onClickNext
        disabled = false
      }
    } else if (nextPrevType === "prev") {
      iconKey = "chevron_left"
      if (currentPage > 1) {
        clickHandler = onClickPrev
        disabled = false
      }
    }
    let className = `paginator-button paginator-${nextPrevType}-button`
    let iconExtraClassNames = ""
    if (disabled) {
      className += " disabled"
    } else {
      className += " activated"
      iconExtraClassNames = "activated"
    }
    // `disabled` is not part of TypeScript's attribute set for <span>, but
    // React still forwards it to the DOM and the rendered markup has always
    // carried it. It is spread in through a widened prop type so the emitted
    // attribute stays exactly as it was.
    const buttonProps: React.HTMLAttributes<HTMLSpanElement> & {
      disabled: boolean
    } = { className, onClick: clickHandler, disabled }
    return (
      <span {...buttonProps}>
        <i className={`material-icons ${iconExtraClassNames}`}>{iconKey}</i>
      </span>
    )
  }

  noop() {}
}

export default Paginator
