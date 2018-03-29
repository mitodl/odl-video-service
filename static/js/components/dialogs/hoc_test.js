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
import { DIALOGS } from "../../constants"
import rootReducer from "../../reducers"
import { INITIAL_UI_STATE } from "../../reducers/commonUi"
import { SHOW_DIALOG, HIDE_DIALOG } from "../../actions/commonUi"

describe("Dialog higher-order component", () => {
  let sandbox, store, listenForActions
  const dialogName = DIALOGS.SHARE_VIDEO
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

  const WrappedTestContainerPage = R.compose(
    connect(state => ({
      commonUi: state.commonUi
    })),
    withDialogs([{ name: dialogName, component: TestDialog }])
  )(TestContainerPage)

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderTestComponentWithDialogs = () =>
    mount(
      <Provider store={store}>
        <WrappedTestContainerPage
          dispatch={store.dispatch}
          commonUi={{ ...INITIAL_UI_STATE }}
        />
      </Provider>
    )

  it("should render the specified dialogs with specific props", () => {
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
      testDialog = wrapper.find('TestDialog')
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
})
