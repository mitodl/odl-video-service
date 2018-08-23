// @flow
import { assert } from "chai"
import sinon from "sinon"

import * as api from "../lib/api"
import { constants, actionCreators } from "./collectionsPagination"

describe("collectionsPagination actions", () => {
  let sandbox, dispatch

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    dispatch = sandbox.spy()
  })

  afterEach(() => {
    sandbox.restore()
  })

  describe("basic action creators", () => {
    [
      {
        actionCreatorName: "requestGetPage",
        constantName:      "REQUEST_GET_PAGE"
      },
      {
        actionCreatorName: "receiveGetPageSuccess",
        constantName:      "RECEIVE_GET_PAGE_SUCCESS"
      },
      {
        actionCreatorName: "receiveGetPageFailure",
        constantName:      "RECEIVE_GET_PAGE_FAILURE"
      }
    ].forEach(actionSpec => {
      it(`has ${actionSpec.actionCreatorName} actionCreator`, () => {
        const payload = "some payload"
        const action = actionCreators[actionSpec.actionCreatorName](payload)
        const expectedAction = {
          type: constants[actionSpec.constantName],
          payload
        }
        assert.deepEqual(action, expectedAction)
      })
    })
  })

  describe("getPage", () => {
    const page = 42
    let stubs = {}

    beforeEach(() => {
      stubs = {
        getCollections:        sandbox.stub(api, "getCollections"),
        requestGetPage:        sandbox.stub(actionCreators, "requestGetPage"),
        receiveGetPageSuccess: sandbox.stub(
          actionCreators,
          "receiveGetPageSuccess"
        ),
        receiveGetPageFailure: sandbox.stub(
          actionCreators,
          "receiveGetPageFailure"
        )
      }
    })

    const _getPage = async () => {
      return actionCreators.getPage({ page })(dispatch)
    }

    it("dispatches REQUEST_GET_PAGE", async () => {
      await _getPage()
      sinon.assert.calledWith(dispatch, stubs.requestGetPage.returnValues[0])
    })

    it("makes api call", async () => {
      await _getPage()
      sinon.assert.calledWith(stubs.getCollections, { pagination: { page } })
    })

    describe("when api call succeeds", () => {
      const response = {
        count:       4242,
        num_pages:   424242,
        results:     [...Array(3).keys()].map(i => ({ key: i })),
        start_index: 99,
        end_index:   999
      }

      beforeEach(() => {
        stubs.getCollections.returns(Promise.resolve(response))
      })

      it("dispatches RECEIVE_GET_PAGE_SUCCESS", async () => {
        await _getPage()
        sinon.assert.calledWith(stubs.receiveGetPageSuccess, {
          page,
          count:       response.count,
          collections: response.results,
          numPages:    response.num_pages,
          startIndex:  response.start_index,
          endIndex:    response.end_index
        })
        sinon.assert.calledWith(
          dispatch,
          stubs.receiveGetPageSuccess.returnValues[0]
        )
      })
    })

    describe("when api call fails", async () => {
      const error = "some error"

      beforeEach(() => {
        stubs.getCollections.returns(Promise.reject(error))
      })

      it("dispatches RECEIVE_GET_PAGE_FAILURE", async () => {
        await _getPage()
        sinon.assert.calledWith(stubs.receiveGetPageFailure, { error, page })
        sinon.assert.calledWith(
          dispatch,
          stubs.receiveGetPageFailure.returnValues[0]
        )
      })
    })
  })
})
