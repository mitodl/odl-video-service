// @flow
/*
 * Rich-text field, drop-in replacement for <Textarea> on description fields.
 *
 * The editor engine is loaded as a split chunk on mount, so the ~117KB of
 * ProseMirror is paid only by an author who opens a form - never by a viewer.
 * Until it arrives the field renders the current value as read-only markup, so
 * the dialog never shows an empty box where text should be.
 *
 * Note this is a class component driving a non-React library through a ref, not
 * because of the React version but because that is how @tiptap/core is meant to
 * be embedded. @tiptap/react does the same thing internally.
 */
import React from "react"

type Props = {
  label: string,
  id: string,
  value: ?string,
  onChange: (html: string) => void,
  // Shown when the field is empty, like a textarea placeholder.
  placeholder?: string
}

type State = {
  // null until the editor chunk has loaded and mounted
  lib: ?Object,
  active: { [string]: boolean },
  // true when the editor chunk could not be fetched; falls back to a textarea
  loadFailed: boolean,
  linkOpen: boolean,
  linkValue: string,
  linkError: boolean
}

export default class RichTextEditor extends React.Component<*, State> {
  props: Props
  editor: ?Object
  editorEl: ?HTMLElement
  linkInput: ?HTMLInputElement
  unmounted: boolean

  constructor(props: Props) {
    super(props)
    this.state = {
      lib:        null,
      active:     {},
      loadFailed: false,
      linkOpen:   false,
      linkValue:  "",
      linkError:  false
    }
    this.unmounted = false
  }

  componentDidMount() {
    // Split point: keeps the editor out of the main bundle.
    import("../../lib/editor")
      .then(lib => {
        if (this.unmounted || !this.editorEl) {
          return
        }
        this.editor = lib.createEditor(
          this.editorEl,
          this.props.value || "",
          this.handleEditorChange
        )
        this.editor.on("selectionUpdate", this.syncActive)
        this.editor.on("transaction", this.syncActive)
        this.setState({ lib }, this.syncActive)
      })
      .catch(error => {
        // Without this the rejection is silent and the field stays a greyed-out
        // box forever - no toolbar, no message, and no way to edit the
        // description. Happens for real when a chunk 404s in a tab that was
        // open across a deploy. Fall back to a plain textarea so the author can
        // still work, in the format the field already stores.
        console.error("Rich-text editor failed to load", error) // eslint-disable-line no-console
        if (!this.unmounted) {
          this.setState({ loadFailed: true })
        }
      })
  }

  componentDidUpdate(prevProps: Props) {
    const { value } = this.props
    if (!this.editor || prevProps.value === value) {
      return
    }
    // Only push a value that came from outside back into the editor. Writing
    // back what the editor itself just emitted would reset the author's cursor
    // to the top of the field on every keystroke.
    if ((value || "") !== this.currentHtml()) {
      this.editor.commands.setContent(value || "", { emitUpdate: false })
    }
  }

  componentWillUnmount() {
    this.unmounted = true
    if (this.editor) {
      this.editor.destroy()
      this.editor = null
    }
  }

  currentHtml(): string {
    const { lib } = this.state
    if (!this.editor || !lib) {
      return ""
    }
    return lib.normalizeHtml(this.editor.getHTML())
  }

  handleEditorChange = (html: string) => {
    this.props.onChange(html)
  }

  focusEditor = () => {
    if (this.editor) {
      this.editor.commands.focus()
    }
  }

  syncActive = () => {
    const { lib } = this.state
    if (!this.editor || !lib) {
      return
    }
    const active = {}
    lib.TOOLBAR_BUTTONS.forEach(button => {
      const target = button.mark || button.node
      active[button.name] = target ? this.editor.isActive(target) : false
    })
    this.setState({ active })
  }

  handleButtonClick = (name: string, event: Object) => {
    // The buttons live inside a form; a bare <button> would submit it.
    event.preventDefault()
    const { lib } = this.state
    if (!this.editor || !lib) {
      return
    }
    if (name === "link") {
      this.openLinkField()
      return
    }
    lib.runCommand(this.editor, name)
    this.syncActive()
  }

  openLinkField = () => {
    const existing =
      this.editor && this.editor.getAttributes("link").href ?
        this.editor.getAttributes("link").href :
        ""
    this.setState(
      { linkOpen: true, linkValue: existing, linkError: false },
      () => {
        if (this.linkInput) {
          this.linkInput.focus()
        }
      }
    )
  }

  closeLinkField = () => {
    this.setState({ linkOpen: false, linkValue: "", linkError: false })
    if (this.editor) {
      this.editor.commands.focus()
    }
  }

  handleLinkChange = (event: Object) => {
    this.setState({ linkValue: event.target.value, linkError: false })
  }

  applyLink = (event: Object) => {
    event.preventDefault()
    const { lib, linkValue } = this.state
    if (!this.editor || !lib) {
      return
    }
    if (lib.applyLink(this.editor, linkValue)) {
      this.closeLinkField()
      this.syncActive()
    } else {
      this.setState({ linkError: true })
    }
  }

  handleLinkKeyDown = (event: Object) => {
    if (event.key === "Enter") {
      this.applyLink(event)
    } else if (event.key === "Escape") {
      event.preventDefault()
      this.closeLinkField()
    }
  }

  renderToolbar() {
    const { lib, active } = this.state
    if (!lib) {
      return null
    }
    return (
      <div className="rte-toolbar" role="toolbar" aria-label="Text formatting">
        {lib.TOOLBAR_BUTTONS.map(button => (
          <button
            type="button"
            key={button.name}
            className={`rte-button${active[button.name] ? " active" : ""}`}
            title={button.title}
            aria-label={button.title}
            aria-pressed={!!active[button.name]}
            onClick={this.handleButtonClick.bind(this, button.name)}
          >
            <i className="material-icons">{button.icon}</i>
          </button>
        ))}
      </div>
    )
  }

  renderLinkField() {
    const { linkOpen, linkValue, linkError } = this.state
    if (!linkOpen) {
      return null
    }
    return (
      <div className="rte-link-row">
        <label className="rte-link-label" htmlFor={`${this.props.id}-link`}>
          Link to
        </label>
        <input
          id={`${this.props.id}-link`}
          className={`rte-link-input${linkError ? " invalid" : ""}`}
          type="text"
          placeholder="https://learn.mit.edu/..."
          value={linkValue}
          ref={el => {
            this.linkInput = el
          }}
          onChange={this.handleLinkChange}
          onKeyDown={this.handleLinkKeyDown}
        />
        <button type="button" className="rte-button" onClick={this.applyLink}>
          Apply
        </button>
        <button
          type="button"
          className="rte-button"
          onClick={this.closeLinkField}
        >
          Cancel
        </button>
        {linkError && (
          <span className="rte-link-error" role="alert">
            Enter a web address or an email link.
          </span>
        )}
      </div>
    )
  }

  handleFallbackChange = (event: Object) => {
    this.props.onChange(event.target.value)
  }

  renderFallback() {
    const { label, id, value, placeholder } = this.props
    return (
      <div className="mdc-textarea-container rte rte-fallback">
        <label htmlFor={id}>{label}</label>
        <p className="rte-fallback-note" role="alert">
          The formatting toolbar could not be loaded. You can still edit the
          description as HTML, or reload the page to try again.
        </p>
        <div className="mdc-text-field">
          <textarea
            className="mdc-text-field__input rich-text-source"
            id={id}
            rows="8"
            spellCheck="false"
            placeholder={placeholder}
            value={value || ""}
            onChange={this.handleFallbackChange}
          />
        </div>
      </div>
    )
  }

  render() {
    const { label, id, value, placeholder } = this.props
    const { lib, loadFailed } = this.state
    if (loadFailed) {
      return this.renderFallback()
    }
    const isEmpty = !value
    return (
      <div className="mdc-textarea-container rte">
        {/*
          No htmlFor: the editable region is a contenteditable div, which is not
          a labelable element, so `for` would point at nothing. aria-labelledby
          on the region gives it its accessible name; the click handler restores
          the click-the-label-to-focus behaviour a real <label> would have.
          */}
        <label id={`${id}-label`} onClick={this.focusEditor}>
          {label}
        </label>
        <div className={`rte-frame${lib ? "" : " loading"}`}>
          {this.renderToolbar()}
          {this.renderLinkField()}
          <div
            id={id}
            className="rte-content"
            aria-labelledby={`${id}-label`}
            ref={el => {
              this.editorEl = el
            }}
          >
            {/*
              Before the chunk lands there is no editor, so show the value as
              markup. Safe to inject: descriptions are sanitized server-side on
              write (ui/html.py) and this is the value the server just sent.
              Once mounted, TipTap owns this element's children.
              */}
            {!lib && !isEmpty && (
              <div dangerouslySetInnerHTML={{ __html: value || "" }} />
            )}
          </div>
          {isEmpty && placeholder && (
            <div className="rte-placeholder" aria-hidden="true">
              {placeholder}
            </div>
          )}
        </div>
      </div>
    )
  }
}
