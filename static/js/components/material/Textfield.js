// @flow
import React from "react"
import R from "ramda"

export default class Textfield extends React.Component {
  props: {
    id: string,
    label?: string,
    validationMessage?: string
  }

  render() {
    const { label, id, validationMessage, ...otherProps } = this.props

    const renderedLabel = label ? <label htmlFor={id}>{label}</label> : null

    return (
      <div className="mdc-textfield-container">
        {renderedLabel}
        <div className="mdc-textfield">
          <input
            type="text"
            className={`${
              validationMessage ? "mdc-textfield__input__invalid" : ""
            } mdc-textfield__input `}
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
