// @flow
/* global React$Element */
import React from "react"

type CheckboxProps = {
  id: string,
  label: string,
  checkGroupName: string,
  value: string,
  checked?: boolean,
  onChange: Function,
  children?: React$Element<*>[],
  className?: string,
  disabled?: boolean
}

export default class Checkbox extends React.Component<*, void> {
  props: CheckboxProps

  render() {
    const {
      value,
      checked,
      checkGroupName,
      id,
      label,
      onChange,
      children,
      className,
      disabled
    } = this.props

    const htmlId = `${checkGroupName}-${id}`

    return (
      <div className={`mdc-form-field ${className || ""}`} key={htmlId}>
        <div
          className={`mdc-checkbox ${disabled ? "mdc-checkbox--disabled" : ""}`}
        >
          <input
            type="checkbox"
            id="basic-checkbox"
            onChange={onChange}
            value={value}
            checked={checked}
            className="mdc-checkbox__native-control"
          />
          <div className="mdc-checkbox__background">
            <svg className="mdc-checkbox__checkmark" viewBox="0 0 24 24">
              <path
                className="mdc-checkbox__checkmark-path"
                fill="none"
                stroke="white"
                d="M1.73,12.91 8.1,19.28 22.79,4.59"
              />
            </svg>
            <div className="mdc-checkbox__mixedmark" />
          </div>
        </div>
        <label htmlFor={htmlId}>{label}</label>
        {children}
      </div>
    )
  }
}
