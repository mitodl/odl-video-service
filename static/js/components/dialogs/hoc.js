// @flow
import React from "react"
import R from "ramda"
import type { Dispatch } from "redux"

import * as commonUiActions from "../../actions/commonUi"
import { getDisplayName } from "../../util/util"

import type { CommonUiState } from "../../reducers/commonUi"

export const withDialogs = R.curry(
  (dialogs: Array<Object>, WrappedComponent) => {
    class WithDialog extends React.Component<*, void> {
      props: {
        dispatch: Dispatch,
        commonUi: CommonUiState
      }

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

        const renderedDialogs = dialogs.map(dialogConfig =>
          React.createElement(dialogConfig.component, {
            key:        dialogConfig.name,
            open:       commonUi.dialogVisibility[dialogConfig.name],
            hideDialog: this.hideDialog.bind(this, dialogConfig.name),
            ...this.props
          })
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

    WithDialog.displayName = `WithDialogs(${getDisplayName(WrappedComponent)})`
    return WithDialog
  }
)
