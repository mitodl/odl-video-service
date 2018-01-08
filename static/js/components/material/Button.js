// @flow
import React from "react"

export default class Button extends React.Component<*, void> {
  render() {
    const { children, className, ...otherProps } = this.props

    return (
      <button
        className={className ? `mdc-button ${className}` : "mdc-button"}
        {...otherProps}
      >
        {children}
      </button>
    )
  }
}
