// @flow
import React from "react"

import RichTextEditor from "./RichTextEditor"
import { DESCRIPTION_FORMAT_HTML } from "../../constants"

type DescriptionFieldProps = {
  label: string,
  id: string,
  placeholder?: string,
  value: ?string,
  descriptionFormat: ?string,
  onChange: (value: string) => void,
  onUpgrade: () => void,
  upgrading?: boolean,
  upgradeError?: ?string
}

/**
 * The description field, in whichever editor suits how the value is stored.
 *
 * A description that is already rich text gets the rich-text editor. One still
 * in plain text gets a plain textarea, and keeps it until the author asks to
 * upgrade - because opening plain text in the rich-text editor would parse it as
 * HTML, collapsing every line break the author typed, and saving would then make
 * that loss permanent. So the upgrade is a decision, not a side effect of
 * opening a dialog.
 *
 * The conversion itself happens on the server (ui.html.upgrade_description),
 * which is the only place that knows how to escape plain text and how to clean
 * markup someone once pasted into the old field. Nothing here reimplements it.
 */
export default class DescriptionField extends React.Component<*, void> {
  props: DescriptionFieldProps

  handleTextChange = (event: Object) => {
    const { onChange } = this.props
    onChange(event.target.value)
  }

  renderRichText() {
    const { label, id, placeholder, value, onChange } = this.props
    return (
      <RichTextEditor
        label={label}
        id={id}
        placeholder={placeholder}
        value={value || ""}
        onChange={onChange}
      />
    )
  }

  renderPlainText() {
    const {
      label,
      id,
      placeholder,
      value,
      onUpgrade,
      upgrading,
      upgradeError
    } = this.props

    return (
      <div className="description-field description-field--plain-text">
        <label htmlFor={id}>{label}</label>
        {/*
         * A real textarea, so the line breaks the author typed stay line
         * breaks. `white-space` is the browser's default here - the field is
         * plain text all the way through.
         */}
        <textarea
          id={id}
          className="description-plain-input"
          rows={8}
          placeholder={placeholder}
          value={value || ""}
          onChange={this.handleTextChange}
        />
        <div className="description-upgrade">
          <p className="description-upgrade__hint">
            This description is plain text, so it has no formatting options.
          </p>
          <button
            type="button"
            className="description-upgrade__button mdc-button"
            onClick={onUpgrade}
            disabled={!!upgrading}
          >
            {upgrading ? "Converting…" : "Use formatting"}
          </button>
          {upgradeError ? (
            <p className="description-upgrade__error">{upgradeError}</p>
          ) : null}
        </div>
      </div>
    )
  }

  render() {
    const { descriptionFormat } = this.props
    return descriptionFormat === DESCRIPTION_FORMAT_HTML ?
      this.renderRichText() :
      this.renderPlainText()
  }
}
