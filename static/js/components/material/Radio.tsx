import React from "react"

type RadioProps = {
  id: string
  label: string
  radioGroupName: string
  value: string
  selectedValue?: string
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void
  children?: React.ReactNode
  className?: string
  disabled?: boolean
}

export default class Radio extends React.Component<RadioProps> {
  render() {
    const {
      value,
      selectedValue,
      radioGroupName,
      id,
      label,
      onChange,
      children,
      className,
      disabled
    } = this.props

    const htmlId = `${radioGroupName}-${id}`

    return (
      <div className={`mdc-form-field ${className || ""}`} key={htmlId}>
        <div className="mdc-radio">
          <input
            type="radio"
            className="mdc-radio__native-control"
            id={htmlId}
            name={radioGroupName}
            value={value}
            onChange={onChange}
            checked={value === selectedValue}
            disabled={disabled || false}
          />
          <div className="mdc-radio__background">
            <div className="mdc-radio__outer-circle" />
            <div className="mdc-radio__inner-circle" />
          </div>
        </div>
        <label htmlFor={htmlId}>{label}</label>
        {children}
      </div>
    )
  }
}
