// @flow
import React from "react"
import * as R from "ramda"

export default class Textfield extends React.Component<*, void> {
  props: {
    id: string,
    label?: string,
    validationMessage?: string
  }

  render() {
    const { label, id, validationMessage, ...otherProps } = this.props

    const renderedLabel = label ? <label htmlFor={id}>{label}</label> : null

    return (
      <div className="mdc-text-field-container">
        {renderedLabel}
        <div className="mdc-text-field">
          <input
            type="text"
            className={`${
              validationMessage ? "mdc-text-field__input__invalid" : ""
            } mdc-text-field__input `}
            id={id}
            {...otherProps}
          />
          {R.isEmpty(validationMessage) || R.isNil(validationMessage) ? null : (
            <div className="validation-message">{validationMessage}</div>
          )}
        </div>
      </div>
    )
  }
}
