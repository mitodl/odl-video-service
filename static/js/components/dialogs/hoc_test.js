import React from "react"
import { assert } from "chai"
import { screen, fireEvent } from "@testing-library/react"
import configureTestStore from "redux-asserts"
import * as R from "ramda"
import { connect } from "react-redux"

import Dialog from "../material/Dialog"
import { withDialogs } from "./hoc"
import rootReducer from "../../reducers"
import { SHOW_DIALOG, HIDE_DIALOG } from "../../actions/commonUi"
import renderWithProviders from "../../testUtils/renderWithProviders"

describe("Dialog higher-order component", () => {
  // dialogProps holds the props withDialogs last handed to the dialog
  // component, captured by reference in TestDialog's render. The dialog's
  // behaviour is asserted through the DOM below; this is only for the props
  // with no rendered form -- `hideDialog` is a callback, so "a function was
  // supplied" is not otherwise observable.
  let store, listenForActions, dialogConfigs, dialogProps
  const dialogName = "some_dialog_name"

  class TestContainerPage extends React.Component {
    render() {
      return (
        <div>
          <button
            id="open-btn"
            onClick={this.props.showDialog.bind(this, dialogName)}
          >
            Open Dialog
          </button>
        </div>
      )
    }
  }

  class TestDialog extends React.Component {
    render() {
      dialogProps = this.props
      return (
        <Dialog
          title="Test Dialog"
          id="test-dialog"
          cancelText="Close"
          submitText=""
          noSubmit={true}
          hideDialog={this.props.hideDialog}
          open={this.props.open}
        >
          Fake Dialog
          {this.props.newProp ? <span>{this.props.newProp}</span> : null}
        </Dialog>
      )
    }
  }

  beforeEach(() => {
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    dialogConfigs = [{ name: dialogName, component: TestDialog }]
    dialogProps = undefined
  })

  const renderTestComponentWithDialogs = (extraProps = {}) => {
    const WrappedTestContainerPage = R.compose(
      connect(state => ({
        commonUi: state.commonUi,
        ...extraProps
      })),
      withDialogs(dialogConfigs)
    )(TestContainerPage)
    return renderWithProviders(
      <WrappedTestContainerPage dispatch={store.dispatch} />,
      { store }
    )
  }

  const isDialogOpen = () =>
    document
      .querySelector("#test-dialog")
      .classList.contains("mdc-dialog--open")

  it("should render the specified dialogs with specific props", () => {
    renderTestComponentWithDialogs()
    assert.exists(screen.queryByText("Fake Dialog"))
    assert.isFalse(isDialogOpen())
    assert.isFalse(dialogProps.open)
    assert.isFunction(dialogProps.hideDialog)
  })

  it("should render dialogs that use lazily evaluated component", () => {
    dialogConfigs = [{ name: dialogName, getComponent: () => TestDialog }]
    renderTestComponentWithDialogs()
    assert.exists(screen.queryByText("Fake Dialog"))
    assert.isFalse(isDialogOpen())
    assert.isFalse(dialogProps.open)
    assert.isFunction(dialogProps.hideDialog)
  })

  it("should provide a function that lets the wrapped component launch the dialog", async () => {
    renderTestComponentWithDialogs()
    assert.isFalse(isDialogOpen())

    await listenForActions([SHOW_DIALOG], () => {
      fireEvent.click(screen.getByRole("button", { name: "Open Dialog" }))
    })

    assert.isTrue(isDialogOpen())
  })

  it("should provide a function that lets the wrapped component hide the dialog", async () => {
    renderTestComponentWithDialogs()

    await listenForActions([SHOW_DIALOG, HIDE_DIALOG], () => {
      fireEvent.click(screen.getByRole("button", { name: "Open Dialog" }))
      fireEvent.click(screen.getByRole("button", { name: "Close" }))
    })
  })

  it("should pass additional props to the dialog component if they are defined", () => {
    renderTestComponentWithDialogs({
      dialogProps: { [dialogName]: { newProp: "newPropValue" } }
    })
    assert.exists(screen.queryByText("Fake Dialog"))
    assert.exists(screen.getByText("newPropValue"))
  })
})
