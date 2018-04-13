// @flow
import { assert } from "chai"
import sinon from "sinon"
import configureTestStore from "redux-asserts"

import rootReducer from "../reducers"
import { actions } from "../actions"


describe("collectionsPagination reducer", () => {
  let store, sandbox, dispatchThen

  beforeEach(() => {
    store = configureTestStore(rootReducer)
    dispatchThen = store.createDispatchThen()
    sandbox = sinon.sandbox.create()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const getPaginationState = () => {
    return store.getState().collectionsPagination
  }

  const getPageState = (page) => {
    return getPaginationState().pages[page]
  }

  const dispatchRequestGetPage = (page) => {
    store.dispatch(actions.collectionsPagination.requestGetPage({page}))
  }

  it("should have some initial state", () => {
    const expectedInitialState = {
      count: 0,
      pages: {},
    }
    assert.deepEqual(getPaginationState(), expectedInitialState)
  })

  describe("REQUEST_GET_PAGE", () => {

    it("sets page status to loading", async () => {
      const page = 42
      assert.notExists(getPageState(page))
      dispatchRequestGetPage(page)
      assert.deepEqual(getPageState(page).status, 'LOADING')
    })
  })

  describe("RECEIVE_GET_PAGE_SUCCESS", () => {
    const page = 42
    const count = 4242
    const collections = [...Array(3).keys()].map((i) => {
      return {"title": `collection${i}`}
    })

    const dispatchReceiveGetPageSuccess = () => {
      store.dispatch(actions.collectionsPagination.receiveGetPageSuccess({count, page, collections}))
    }

    beforeEach(() => {
      dispatchRequestGetPage(page)
    })

    it("updates count", async () => {
      assert.equal(getPaginationState().count, 0)
      dispatchReceiveGetPageSuccess()
      assert.equal(getPaginationState().count, count)
    })

    it("updates page status", async () => {
      assert.notEqual(getPageState(page).status, 'LOADED')
      dispatchReceiveGetPageSuccess()
      assert.equal(getPageState(page).status, 'LOADED')
    })

    it("updates page collections", async () => {
      assert.notDeepEqual(getPageState(page).collections, collections)
      dispatchReceiveGetPageSuccess()
      assert.deepEqual(getPageState(page).collections, collections)
    })
  })

  describe("RECEIVE_GET_PAGE_FAILURE", () => {

    const page = 42
    const error = 'some_error'

    const dispatchReceiveGetPageFailure = () => {
      store.dispatch(actions.collectionsPagination.receiveGetPageFailure({page, error}))
    }

    beforeEach(() => {
      dispatchRequestGetPage(page)
    })

    it("updates page status", async () => {
      assert.notEqual(getPageState(page).status, 'ERROR')
      dispatchReceiveGetPageFailure()
      assert.equal(getPageState(page).status, 'ERROR')
    })

    it("updates page error", async () => {
      assert.notExists(getPageState(page).error)
      dispatchReceiveGetPageFailure()
      assert.equal(getPageState(page).error, error)
    })
  })

  describe("SET_CURRENT_PAGE", () => {
    it("sets currentPage", () => {
      const currentPage = 42
      assert.notEqual(getPaginationState().currentPage, currentPage)
      store.dispatch(actions.collectionsPagination.setCurrentPage({currentPage})
      assert.equal(getPaginationState().currentPage, currentPage)
    })
  })

})
