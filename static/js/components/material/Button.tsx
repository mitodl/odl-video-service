import React from "react"

type Props = React.ButtonHTMLAttributes<HTMLButtonElement>

export default class Button extends React.Component<Props> {
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
