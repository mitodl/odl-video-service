// @flow
/* global SETTINGS: false */
import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { mount } from "enzyme"

import { actions } from "../actions"

import { mapStateToProps, withPagedCollections } from './withPagedCollections'


describe("withPagedCollections", () => {
  let sandbox

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
  })

  afterEach(() => {
    sandbox.restore()
  })

  describe("mapStateToProps", () => {
    describe("currentCollectionsPageNeedsUpdate", () => {
      it("is true when current page state is undefined", () => {
        const state = {
          collectionsPagination: {
            count:       0,
            currentPage: 42,
            pages:       {},
          }
        }
        const props = mapStateToProps(state)
        assert.equal(props.collectionsCurrentPageNeedsUpdate, true)
      })

      it("is false when current page status is defined", () => {
        const state = {
          collectionsPagination: {
            count:       0,
            currentPage: 42,
            pages:       {
              42: {}
            },
          }
        }
        const props = mapStateToProps(state)
        assert.equal(props.collectionsCurrentPageNeedsUpdate, false)
      })
    })

    it("selects currentPage", () => {
      const currentPage = 42
      const state = { collectionsPagination: { currentPage } }
      const props = mapStateToProps(state)
      assert.equal(props.collectionsCurrentPage, currentPage)
    })

    it("selects current page data", () => {
      const currentPage = 42
      const state = {
        collectionsPagination: {
          count: 0,
          currentPage,
          pages: {
            [currentPage]: {
              collections: [],
              status:      'some status',
            }
          },
        }
      }
      const props = mapStateToProps(state)
      assert.equal(
        props.collectionsCurrentPageData,
        state.collectionsPagination.pages[currentPage]
      )
    })

    it("selects count", () => {
      const count = 42
      const state = {
        collectionsPagination: {
          count,
        }
      }
      const props = mapStateToProps(state)
      assert.equal(props.collectionsCount, count)
    })
  })

  describe("WrappedComponent", () => {
    class DummyComponent extends React.Component {
      render () {
        return (<div>DummyComponent</div>)
      }
    }

    const WrappedComponent = withPagedCollections(DummyComponent)

    describe("page updates", () => {
      let stubs

      beforeEach(() => {
        stubs = {
          updateCollectionsCurrentPage: sandbox.stub(
            WrappedComponent.prototype,
            "updateCollectionsCurrentPage"
          ),
        }
      })

      describe("when collectionsCurrentPageNeedsUpdate is true", () => {
        it("calls updateCurrentPage", () => {
          mount(
            <WrappedComponent
              collectionsCurrentPageNeedsUpdate={true}
            />
          )
          sinon.assert.called(stubs.updateCollectionsCurrentPage)
        })
      })

      describe("when pageNeedsUpdate is false", () => {
        it("does not dispatch getPage action", () => {
          mount(
            <WrappedComponent
              collectionsCurrentPageNeedsUpdate={false}
            />
          )
          sinon.assert.notCalled(stubs.updateCollectionsCurrentPage)
        })
      })
    })

    describe("updateCollectionsCurrentPage", () => {
      let stubs

      beforeEach(() => {
        stubs = {
          dispatch: sandbox.spy(),
          getPage:  sandbox.stub(actions.collectionsPagination, 'getPage'),
        }
      })

      it("dispatches getPage action with currentPage", () => {
        const collectionsCurrentPage = 42
        mount(
          <WrappedComponent
            dispatch={stubs.dispatch}
            collectionsCurrentPageNeedsUpdate={true}
            collectionsCurrentPage={collectionsCurrentPage}
          />
        )
        sinon.assert.calledWith(
          stubs.getPage,
          {page: collectionsCurrentPage}
        )
        sinon.assert.calledWith(stubs.dispatch, stubs.getPage.returnValues[0])
      })
    })
  })
})
