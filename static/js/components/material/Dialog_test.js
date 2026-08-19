// @flow
import React from "react"
import { mount } from "enzyme"
import sinon from "sinon"

import Dialog from "./Dialog"

describe("Dialog", () => {
  let sandbox

  beforeEach(() => {
    sandbox = sinon.createSandbox()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderDialog = (props = {}) =>
    mount(
      <Dialog
        id="test-dialog"
        open={false}
        hideDialog={sandbox.stub()}
        cancelText="Cancel"
        submitText="Save"
        {...props}
      >
        <div>content</div>
      </Dialog>
    )

  // componentDidUpdate replaced componentWillReceiveProps here, which also
  // inverted the prop comparison (prevProps.open !== this.props.open vs.
  // the old this.props.open !== nextProps.open). This is the regression
  // this test is meant to catch: getting that comparison backwards would
  // either skip a real toggle or fire on every unrelated prop change.
  it("shows and destroys the MDC dialog as the open prop toggles, including a reopen", () => {
    const wrapper = renderDialog({ open: false })
    const instance = wrapper.instance()
    const showSpy = sandbox.spy(instance, "showMdc")
    const destroySpy = sandbox.spy(instance, "destroyMdc")

    wrapper.setProps({ open: true })
    sinon.assert.calledOnce(showSpy)
    sinon.assert.notCalled(destroySpy)

    wrapper.setProps({ open: false })
    sinon.assert.calledOnce(showSpy)
    sinon.assert.calledOnce(destroySpy)

    wrapper.setProps({ open: true })
    sinon.assert.calledTwice(showSpy)
    sinon.assert.calledOnce(destroySpy)
  })

  it("does not call showMdc/destroyMdc when an unrelated prop changes", () => {
    const wrapper = renderDialog({ open: false })
    const instance = wrapper.instance()
    const showSpy = sandbox.spy(instance, "showMdc")
    const destroySpy = sandbox.spy(instance, "destroyMdc")

    wrapper.setProps({ title: "A new title" })
    sinon.assert.notCalled(showSpy)
    sinon.assert.notCalled(destroySpy)
  })
})
