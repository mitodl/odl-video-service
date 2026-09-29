import React from "react"

type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string
  id: string
}

export default class Textarea extends React.Component<TextareaProps> {
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
