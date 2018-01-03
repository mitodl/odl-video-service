// @flow
import React from "react"

export default class Filefield extends React.Component<*, void> {
  fileInput: ?HTMLElement
  props: {
    label?: string,
    accept?: string,
    className?: string
  }

  handleClick = () => {
    if (this.fileInput) {
      const uploadBtn = this.fileInput
      // $FlowFixMe: I'm not sure if null is a valid value for this (maybe '' is better) but I don't want to change it
      uploadBtn.value = null
      uploadBtn.click()
    }
  }

  render() {
    const { label, accept, className, ...otherProps } = this.props

    const acceptedTypes = accept ? accept : "*"

    return (
      <button
        onClick={this.handleClick}
        href="#"
        className={
          className
            ? `${className} button-link upload-link`
            : "button-link upload-link"
        }
      >
        <input
          type="file"
          className="hidden upload-input"
          ref={input => {
            this.fileInput = input
          }}
          accept={acceptedTypes}
          {...otherProps}
        />
        {label}
      </button>
    )
  }
}
