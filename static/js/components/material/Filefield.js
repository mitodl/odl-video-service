// @flow
import React from "react"

export default class Filefield extends React.Component {
  fileInput: null
  props: {
    label?: string,
    accept?: string,
    className?: string
  }

  handleClick = () => {
    if (this.fileInput) {
      const uploadBtn = this.fileInput
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
