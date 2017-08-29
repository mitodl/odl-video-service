// @flow
import React from 'react';
import {MDCDialog} from '@material/dialog/dist/mdc.dialog';

import Button from './Button';

type DialogProps = {
  open: boolean,
  onAccept: () => void,
  onCancel: () => void,
  children: React.Children,
  title: string,
  cancelText: string,
  submitText: string,
  noSubmit: boolean,
  id: string
};

export default class Dialog extends React.Component {
  dialog: null;
  dialogRoot: null;
  // $FlowFixMe: Flow doesn't like the extra props that aren't part of mdc.dialog class
  props: DialogProps;

  componentDidMount() {
    const { open, onAccept, onCancel } = this.props;
    this.dialog = new MDCDialog(this.dialogRoot);

    this.dialog.listen('MDCDialog:accept', onAccept);
    // $FlowFixMe: Flow thinks this.dialog might be null
    this.dialog.listen('MDCDialog:cancel', onCancel);

    if (open) {
      // $FlowFixMe: Flow thinks this.dialog might be null
      this.dialog.show();
    }
  }

  componentWillUnmount() {
    if (this.dialog) {
      this.dialog.destroy();
    }
  }

  componentWillReceiveProps(nextProps: DialogProps) {
    if (this.dialog) {
      if (this.props.open !== nextProps.open) {
        if (nextProps.open) {
          this.dialog.show();
        } else {
          this.dialog.close();
        }
      }
    }
  }

  render() {
    const { title, children, cancelText, submitText, noSubmit, id } = this.props;

    return <aside
      id={id ? id : 'mdc-dialog'}
      className="mdc-dialog"
      role="alertdialog"
      aria-labelledby="my-mdc-dialog-label"
      aria-describedby="my-mdc-dialog-description"
      ref={node => this.dialogRoot = node}
    >
      <div className="mdc-dialog__surface">
        <header className="mdc-dialog__header">
          <h2 id="my-mdc-dialog-label" className="mdc-dialog__header__title">
            {title}
          </h2>
        </header>
        <section id="my-mdc-dialog-description" className="mdc-dialog__body">
          {children}
        </section>
        <footer className="mdc-dialog__footer">
          <Button type="button" className="mdc-dialog__footer__button mdc-dialog__footer__button--cancel cancel-button">
            {cancelText || 'Cancel'}
          </Button>
          {noSubmit ? null : (
            <Button
              type="button"
              className="mdc-dialog__footer__button mdc-dialog__footer__button--accept edit-button">
              {submitText || 'Save'}
            </Button>)}
        </footer>
      </div>
      <div className="mdc-dialog__backdrop"/>
    </aside>;
  }

}
