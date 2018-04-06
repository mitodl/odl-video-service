// @flow
import React from "react"

export default class Textarea extends React.Component<*, void> {
  props: {
    label: string,
    id: string
  }

  render() {
    const { label, id, ...otherProps } = this.props
    return (
      <div className="mdc-textarea-container">
        <label htmlFor={id}>{label}</label>
        <div className="mdc-text-field">
          <textarea className="mdc-text-field__input" id={id} {...otherProps} />
        </div>
      </div>
    )
  }
}
