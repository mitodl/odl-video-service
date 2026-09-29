import React from "react"
import { MDCDialog } from "@material/dialog/dist/mdc.dialog"

import Button from "./Button"

/*
 * @material/dialog 0.33 ships no type declarations, so the instance is typed
 * by the three members this component actually uses of it.
 */
type MDCDialogInstance = {
  listen: (eventName: string, handler: () => void) => void
  show: () => void
  destroy: () => void
}

type DialogProps = {
  open: boolean
  onAccept?: () => void
  onCancel?: () => void
  hideDialog: () => void
  children: React.ReactNode
  title?: string
  // Both are optional: render() falls back to "Cancel"/"Save" when they are
  // absent, and the submit button is not rendered at all under noSubmit -- so
  // callers that pass noSubmit legitimately omit submitText.
  cancelText?: string
  submitText?: string
  noSubmit?: boolean
  id: string
  validateOnClick?: boolean
}

export default class Dialog extends React.Component<DialogProps> {
  dialog: MDCDialogInstance | null
  dialogRoot: HTMLElement | null

  componentDidMount() {
    const { open } = this.props

    // Hack to get dialog to play nicely with JS tests
    if (!this.dialogRoot || !this.dialogRoot.dataset) return

    this.dialog = new MDCDialog(this.dialogRoot)
    this.attachDialogListeners(this.dialog)

    if (open) {
      this.showMdc()
    }
  }

  componentWillUnmount() {
    this.destroyMdc()
  }

  componentDidUpdate(prevProps: DialogProps) {
    if (prevProps.open !== this.props.open) {
      if (this.props.open) {
        this.showMdc()
      } else {
        this.destroyMdc()
      }
    }
  }

  // This function only exists because of false Flow errors
  attachDialogListeners = (dialog: MDCDialogInstance) => {
    const { onAccept, onCancel, hideDialog, validateOnClick } = this.props

    if (onAccept) {
      dialog.listen("MDCDialog:accept", onAccept)
    }
    if (!validateOnClick) {
      dialog.listen("MDCDialog:accept", hideDialog)
    }
    if (onCancel) {
      dialog.listen("MDCDialog:cancel", onCancel)
    }
    dialog.listen("MDCDialog:cancel", hideDialog)
  }

  showMdc() {
    if (this.dialog) {
      this.dialog.show()
    }
  }

  destroyMdc() {
    if (this.dialog) {
      this.dialog.destroy()
    }
  }

  render() {
    const {
      title,
      children,
      cancelText,
      submitText,
      noSubmit,
      id,
      open,
      onCancel,
      onAccept,
      validateOnClick
    } = this.props

    // Hack to avoid showing unstyled dialog contents before the stylesheets are ready
    const styleProp = open ? {} : { display: "none" }

    return (
      <aside
        id={id}
        className="mdc-dialog"
        role="alertdialog"
        aria-labelledby="my-mdc-dialog-label"
        aria-describedby="my-mdc-dialog-description"
        style={styleProp}
        ref={node => {
          this.dialogRoot = node
        }}
      >
        <div className="mdc-dialog__surface">
          {title ? (
            <header className="mdc-dialog__header">
              <h2
                id="my-mdc-dialog-label"
                className="mdc-dialog__header__title"
              >
                {title}
              </h2>
            </header>
          ) : null}
          <section id="my-mdc-dialog-description" className="mdc-dialog__body">
            {children}
          </section>
          <footer className="mdc-dialog__footer">
            <Button
              type="button"
              onClick={onCancel}
              className={`mdc-dialog__footer__button cancel-button
              ${!validateOnClick ? "mdc-dialog__footer__button--cancel" : ""}`}
            >
              {cancelText || "Cancel"}
            </Button>
            {noSubmit ? null : (
              <Button
                type="button"
                onClick={onAccept}
                className={`mdc-dialog__footer__button edit-button
                ${
              !validateOnClick ? "mdc-dialog__footer__button--accept" : ""
              }`}
              >
                {submitText || "Save"}
              </Button>
            )}
          </footer>
        </div>
        <div className="mdc-dialog__backdrop" />
      </aside>
    )
  }
}
