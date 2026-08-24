// @flow
/* global SETTINGS: false */
import React from "react"
import _ from "lodash"
import { assert } from "chai"
import sinon from "sinon"
import { render } from "@testing-library/react"

import { actions } from "../actions"

import { mapStateToProps, withPagedCollections } from "./withPagedCollections"

describe("withPagedCollections", () => {
  let sandbox

  beforeEach(() => {
    sandbox = sinon.createSandbox()
  })

  afterEach(() => {
    sandbox.restore()
  })

  describe("mapStateToProps", () => {
    describe("needsUpdate", () => {
      it("is true when current page state is undefined", () => {
        const state = {
          collectionsPagination: {
            count:       0,
            currentPage: 42,
            pages:       {}
          }
        }
        const props = mapStateToProps(state)
        assert.equal(props.needsUpdate, true)
      })

      it("is false when current page status is defined", () => {
        const state = {
          collectionsPagination: {
            count:       0,
            currentPage: 42,
            pages:       {
              // $FlowFixMe
              42: {}
            }
          }
        }
        const props = mapStateToProps(state)
        assert.equal(props.needsUpdate, false)
      })
    })

    it("passes collectionsPagination state", () => {
      const state = {
        collectionsPagination: {
          someKey:      "someValue",
          someOtherKey: "someOtherValue"
        }
      }
      const props = mapStateToProps(state)
      assert.equal(props.collectionsPagination, state.collectionsPagination)
    })
  })

  describe("WrappedComponent", () => {
    class DummyComponent extends React.Component<*, void> {
      render() {
        return <div>DummyComponent</div>
      }
    }

    const WrappedComponent = withPagedCollections(DummyComponent)

    describe("page updates", () => {
      let stubs

      beforeEach(() => {
        stubs = {
          updateCurrentPage: sandbox.stub(
            WrappedComponent.prototype,
            "updateCurrentPage"
          )
        }
      })

      describe("when needsUpdate is true", () => {
        it("calls updateCurrentPage", () => {
          render(<WrappedComponent needsUpdate={true} />)
          sinon.assert.called(stubs.updateCurrentPage)
        })
      })

      describe("when pageNeedsUpdate is false", () => {
        it("does not dispatch getPage action", () => {
          render(<WrappedComponent needsUpdate={false} />)
          sinon.assert.notCalled(stubs.updateCurrentPage)
        })
      })
    })

    describe("updateCurrentPage", () => {
      let stubs

      beforeEach(() => {
        stubs = {
          dispatch: sandbox.spy(),
          getPage:  sandbox.stub(actions.collectionsPagination, "getPage")
        }
      })

      it("dispatches getPage action with currentPage", () => {
        const currentPage = 42
        render(
          <WrappedComponent
            dispatch={stubs.dispatch}
            needsUpdate={true}
            collectionsPagination={{ currentPage }}
          />
        )
        sinon.assert.calledWith(stubs.getPage, { page: currentPage })
        sinon.assert.calledWith(stubs.dispatch, stubs.getPage.returnValues[0])
      })
    })

    describe("generatePropsForWrappedComponent", () => {
      it("passes on expected props", () => {
        const extraProps = { someKey: "someVal", someOtherKey: "someOtherVal" }
        const currentPage = 42
        const collectionsPagination = {
          currentPage,
          pages: {
            [currentPage]: {
              somePageDataKey: "somePageDataValue"
            }
          }
        }
        // DummyComponent (above, test-owned) renders only static text with
        // no way to read back the object/function props it received via the
        // DOM (confirmed via Rule 26 DOM capture of the Enzyme version:
        // `wrapper.html()` was `<div>DummyComponent</div>`, no prop data).
        // Spy on its own `render` and read `thisValue.props` -- the same
        // technique VideoCard_test.js uses for Menu.prototype.render.
        const renderSpy = sandbox.spy(DummyComponent.prototype, "render")
        const dispatch = sandbox.spy()
        const setCurrentPageStub = sandbox.stub(
          actions.collectionsPagination,
          "setCurrentPage"
        )

        render(
          <WrappedComponent
            {...extraProps}
            dispatch={dispatch}
            collectionsPagination={collectionsPagination}
          />
        )

        const receivedProps = renderSpy.lastCall.thisValue.props

        // Structural facts: extraProps pass through unchanged, and
        // currentPageData is derived correctly from
        // collectionsPagination.pages[currentPage].
        assert.deepEqual(_.omit(receivedProps, ["collectionsPagination"]), {
          ...extraProps,
          dispatch
        })
        assert.deepEqual(
          _.omit(receivedProps.collectionsPagination, ["setCurrentPage"]),
          {
            ...collectionsPagination,
            currentPageData: collectionsPagination.pages[currentPage]
          }
        )

        // Functional fact, replacing the original's bare `===` check against
        // `wrapper.instance().setCurrentPage` (RTL has no equivalent way to
        // fetch "the instance" independently of the rendered props to compare
        // against). Invoking the received prop and asserting it dispatches
        // through the real instance is strictly stronger evidence that it
        // *is* `WithPagedCollections.prototype.setCurrentPage` bound to this
        // instance than a reference-identity check ever was -- and it closes
        // a real coverage gap, since nothing else in this file invokes
        // `setCurrentPage` and checks its dispatch behavior. Deliberate
        // strengthening, called out per Rule 2 in the commit message.
        receivedProps.collectionsPagination.setCurrentPage(99)
        sinon.assert.calledWith(setCurrentPageStub, { currentPage: 99 })
        sinon.assert.calledWith(dispatch, setCurrentPageStub.returnValues[0])
      })
    })
  })
})
