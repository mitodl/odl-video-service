import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { mount } from "enzyme"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"
import R from "ramda"
import { connect } from "react-redux"

import Dialog from "../material/Dialog"
import { withDialogs } from "./hoc"
import rootReducer from "../../reducers"
import { SHOW_DIALOG, HIDE_DIALOG } from "../../actions/commonUi"

describe("Dialog higher-order component", () => {
  let sandbox, store, listenForActions, dialogConfigs
  const dialogName = "some_dialog_name"
  const selectors = {
    OPEN_BTN:  "#open-btn",
    CLOSE_BTN: ".cancel-button"
  }

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
        </Dialog>
      )
    }
  }

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    dialogConfigs = [{ name: dialogName, component: TestDialog }]
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderTestComponentWithDialogs = (extraProps = {}) => {
    const WrappedTestContainerPage = R.compose(
      connect(state => ({
        commonUi: state.commonUi,
        ...extraProps
      })),
      withDialogs(dialogConfigs)
    )(TestContainerPage)
    return mount(
      <Provider store={store}>
        <WrappedTestContainerPage dispatch={store.dispatch} />
      </Provider>
    )
  }

  it("should render the specified dialogs with specific props", () => {
    const wrapper = renderTestComponentWithDialogs()
    const testDialog = wrapper.find("TestDialog")
    assert.isTrue(testDialog.exists())
    assert.isFalse(testDialog.props().open)
    assert.isFunction(testDialog.props().hideDialog)
  })

  it("should render dialogs that use lazily evaluated component", () => {
    dialogConfigs = [{ name: dialogName, getComponent: () => TestDialog }]
    const wrapper = renderTestComponentWithDialogs()
    const testDialog = wrapper.find("TestDialog")
    assert.isTrue(testDialog.exists())
    assert.isFalse(testDialog.props().open)
    assert.isFunction(testDialog.props().hideDialog)
  })

  it("should provide a function that lets the wrapped component launch the dialog", async () => {
    const wrapper = renderTestComponentWithDialogs()
    let testDialog = wrapper.find("TestDialog")
    assert.isFalse(testDialog.prop("open"))
    assert.isFalse(testDialog.find("Dialog").prop("open"))

    return await listenForActions([SHOW_DIALOG], () => {
      wrapper.find(selectors.OPEN_BTN).prop("onClick")()
    }).then(() => {
      wrapper.update()
      testDialog = wrapper.find("TestDialog")
      assert.isTrue(testDialog.prop("open"))
      assert.isTrue(testDialog.find("Dialog").prop("open"))
    })
  })

  it("should provide a function that lets the wrapped component hide the dialog", async () => {
    const wrapper = renderTestComponentWithDialogs()
    await listenForActions([SHOW_DIALOG, HIDE_DIALOG], () => {
      wrapper.find(selectors.OPEN_BTN).prop("onClick")()
      wrapper.find("Dialog").prop("hideDialog")()
    })
  })

  it("should pass additional props to the dialog component if they are defined", async () => {
    const wrapper = renderTestComponentWithDialogs({
      dialogProps: { [dialogName]: { newProp: "newPropValue" } }
    })
    const testDialog = wrapper.find("TestDialog")
    assert.isTrue(testDialog.exists())
    const addedPropValue = testDialog.prop("newProp")
    assert.isString(addedPropValue)
    assert.equal(addedPropValue, "newPropValue")
  })
})
