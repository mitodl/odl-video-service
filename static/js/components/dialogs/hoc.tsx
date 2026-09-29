import React from "react"
import * as R from "ramda"
import type { Dispatch } from "redux"

import * as commonUiActions from "../../actions/commonUi"
import { getDisplayName } from "../../util/util"

import type { CommonUiState } from "../../reducers/commonUi"

/*
 * A dialog is configured either by `component` (what every container does) or
 * by `getComponent`, a thunk that defers resolving the component until render.
 * Both are optional so either form typechecks; exactly one is expected.
 */
type DialogConfig = {
  name: string
  component?: React.ComponentType<Record<string, unknown>>
  getComponent?: () => React.ComponentType<Record<string, unknown>>
}

type Props = {
  dispatch: Dispatch
  commonUi: CommonUiState
  dialogProps?: { [key: string]: Record<string, unknown> }
  // Every other prop is forwarded untouched to the wrapped component and to
  // each dialog.
  [key: string]: unknown
}

export const withDialogs = R.curry(
  (
    dialogs: Array<DialogConfig>,
    WrappedComponent: React.ComponentType<Record<string, unknown>>
  ) => {
    class WithDialog extends React.Component<Props> {
      showDialog = (dialogName: string) => {
        const { dispatch } = this.props
        dispatch(commonUiActions.showDialog(dialogName))
      }

      hideDialog = (dialogName: string) => {
        const { dispatch } = this.props
        dispatch(commonUiActions.hideDialog(dialogName))
      }

      render() {
        const { commonUi } = this.props
        const dialogProps = this.props.dialogProps || {}

        const renderedDialogs = dialogs.map(dialogConfig =>
          React.createElement(
            dialogConfig.getComponent ?
              dialogConfig.getComponent() :
              dialogConfig.component,
            {
              key: dialogConfig.name,
              open:
                commonUi.dialogVisibility &&
                !!commonUi.dialogVisibility[dialogConfig.name],
              hideDialog: this.hideDialog.bind(this, dialogConfig.name),
              ...(dialogProps[dialogConfig.name] || {}),
              ...this.props
            }
          )
        )

        return (
          <div>
            <WrappedComponent
              {...this.props}
              showDialog={this.showDialog}
              hideDialog={this.hideDialog}
            />
            {renderedDialogs}
          </div>
        )
      }
    }

    // tsc will not let a static be added to a class declaration after the
    // fact; the cast is erased at runtime, so this stays the same assignment
    // on the same class object.
    (WithDialog as React.ComponentClass<Props>).displayName =
      `WithDialogs(${getDisplayName(WrappedComponent)})`
    return WithDialog
  }
)
