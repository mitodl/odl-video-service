// @flow
import React from "react"


export default class ErrorMessage extends React.Component<*, void> {
  render() {
    const { children, className, ...passThroughProps } = this.props
    let classNames = ["odl-error-message"]
    if (className) { classNames = [...classNames, className] }
    return (
      <div className={classNames.join(" ")} {...passThroughProps}>
        {children}
      </div>
    )
  }
}
