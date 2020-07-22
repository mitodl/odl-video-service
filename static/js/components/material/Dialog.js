// @flow
import React from "react"
import { MDCDialog } from "@material/dialog/dist/mdc.dialog"

import type { ChildrenArray } from "react"

import Button from "./Button"

type DialogProps = {
  open: boolean,
  onAccept?: () => void,
  onCancel?: () => void,
  hideDialog: () => void,
  children: ChildrenArray<*>,
  title?: string,
  cancelText: string,
  submitText: string,
  noSubmit?: boolean,
  id: string,
  validateOnClick?: boolean
}

export default class Dialog extends React.Component<*, void> {
  dialog: null
  dialogRoot: ?HTMLElement
  // $FlowFixMe: Flow doesn't like the extra props that aren't part of mdc.dialog class
  props: DialogProps

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

  // eslint-disable-next-line react/no-deprecated
  componentWillReceiveProps(nextProps: DialogProps) {
    if (this.props.open !== nextProps.open) {
      if (nextProps.open) {
        this.showMdc()
      } else {
        this.destroyMdc()
      }
    }
  }

  // This function only exists because of false Flow errors
  attachDialogListeners = (dialog: Object) => {
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
        ref={node => (this.dialogRoot = node)}
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
