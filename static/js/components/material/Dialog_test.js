// @flow
import React from "react"
import { render } from "@testing-library/react"
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
    render(
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
  //
  // showMdc/destroyMdc are plain Dialog.prototype methods, so they're
  // spied on the prototype and installed before the initial render -- the
  // same "stub Prototype.method" boundary VideoPlayer_test.js uses for
  // VideoPlayerController.prototype.cropVideo. This is a real timing
  // difference from the Enzyme original, which spied on the mounted
  // instance *after* mount: here the spy is live during the initial mount
  // too. That's harmless for this test because the initial mount always
  // uses open=false (componentDidMount only calls showMdc() when open is
  // truthy), so neither spy fires at mount either way.
  it("shows and destroys the MDC dialog as the open prop toggles, including a reopen", () => {
    const showSpy = sandbox.spy(Dialog.prototype, "showMdc")
    const destroySpy = sandbox.spy(Dialog.prototype, "destroyMdc")
    const { rerender } = renderDialog({ open: false })

    rerender(
      <Dialog
        id="test-dialog"
        open={true}
        hideDialog={sandbox.stub()}
        cancelText="Cancel"
        submitText="Save"
      >
        <div>content</div>
      </Dialog>
    )
    sinon.assert.calledOnce(showSpy)
    sinon.assert.notCalled(destroySpy)

    rerender(
      <Dialog
        id="test-dialog"
        open={false}
        hideDialog={sandbox.stub()}
        cancelText="Cancel"
        submitText="Save"
      >
        <div>content</div>
      </Dialog>
    )
    sinon.assert.calledOnce(showSpy)
    sinon.assert.calledOnce(destroySpy)

    rerender(
      <Dialog
        id="test-dialog"
        open={true}
        hideDialog={sandbox.stub()}
        cancelText="Cancel"
        submitText="Save"
      >
        <div>content</div>
      </Dialog>
    )
    sinon.assert.calledTwice(showSpy)
    sinon.assert.calledOnce(destroySpy)
  })

  it("does not call showMdc/destroyMdc when an unrelated prop changes", () => {
    const showSpy = sandbox.spy(Dialog.prototype, "showMdc")
    const destroySpy = sandbox.spy(Dialog.prototype, "destroyMdc")
    const { rerender } = renderDialog({ open: false })

    rerender(
      <Dialog
        id="test-dialog"
        open={false}
        hideDialog={sandbox.stub()}
        cancelText="Cancel"
        submitText="Save"
        title="A new title"
      >
        <div>content</div>
      </Dialog>
    )
    sinon.assert.notCalled(showSpy)
    sinon.assert.notCalled(destroySpy)
  })
})
