// @flow
/* global SETTINGS: false */
import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { mount } from "enzyme"

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
          mount(<WrappedComponent needsUpdate={true} />)
          sinon.assert.called(stubs.updateCurrentPage)
        })
      })

      describe("when pageNeedsUpdate is false", () => {
        it("does not dispatch getPage action", () => {
          mount(<WrappedComponent needsUpdate={false} />)
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
        mount(
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
        const wrapper = mount(
          <WrappedComponent
            {...extraProps}
            collectionsPagination={collectionsPagination}
          />
        )
        const wrapped = wrapper.find("DummyComponent")
        assert.deepEqual(wrapped.props(), {
          ...extraProps,
          collectionsPagination: {
            ...collectionsPagination,
            setCurrentPage:  wrapper.instance().setCurrentPage,
            currentPageData: collectionsPagination.pages[currentPage]
          }
        })
      })
    })
  })
})
