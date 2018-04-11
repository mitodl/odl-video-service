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
        constantName:      "REQUEST_GET_PAGE",
      },
      {
        actionCreatorName: "receiveGetPageSuccess",
        constantName:      "RECEIVE_GET_PAGE_SUCCESS",
      },
      {
        actionCreatorName: "receiveGetPageFailure",
        constantName:      "RECEIVE_GET_PAGE_FAILURE",
      },
    ].forEach((actionSpec) => {
      it(`has ${actionSpec.actionCreatorName} actionCreator`, () => {
        const payload = 'some payload'
        const action = actionCreators[actionSpec.actionCreatorName](payload)
        const expectedAction = {
          type: constants[actionSpec.constantName],
          payload,
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
        getCollections:        sandbox.stub(
          api, 'getCollections'),
        requestGetPage:        sandbox.stub(
          actionCreators, 'requestGetPage'),
        receiveGetPageSuccess: sandbox.stub(
          actionCreators, 'receiveGetPageSuccess'),
        receiveGetPageFailure: sandbox.stub(
          actionCreators, 'receiveGetPageFailure'),
      }
    })

    const _getPage = async () => {
      return actionCreators.getPage(page)(dispatch)
    }

    it("dispatches REQUEST_GET_PAGE", async () => {
      await _getPage()
      sinon.assert.calledWith(
        dispatch,
        stubs.requestGetPage.returnValues[0]
      )
    })

    it("makes api call", async () => {
      await _getPage()
      sinon.assert.calledWith(stubs.getCollections, { page })
    })

    describe("when api call succeeds", () => {
      const result = {
        data: {
          count:   4242,
          results: [...Array(3).keys()].map((i) => ({key: i})),
        },
      }

      beforeEach(() => {
        stubs.getCollections.returns(Promise.resolve(result))
      })

      it("dispatches RECEIVE_COLLECTIONS", async () => {
        await _getPage()
        sinon.assert.calledWith(stubs.hmm, result.data.results)
        sinon.assert.calledWith(
          dispatch,
          stubs.hmm.returnValues[0]
        )
      })

      it("dispatches RECEIVE_GET_PAGE_SUCCESS", async () => {
        await _getPage()
        sinon.assert.calledWith(
          stubs.receiveGetPageSuccess,
          {
            count:      result.data.count,
            entityKeys: (
              result.data.results.map((collection) => collection.key)
            ),
            page,
          }
        )
        sinon.assert.calledWith(
          dispatch,
          stubs.receiveGetPageSuccess.returnValues[0]
        )
      })
    })

    describe("when api call fails", async () => {
      const error = 'some error'

      beforeEach(() => {
        stubs.getCollections.returns(Promise.reject(error))
      })

      it("dispatches RECEIVE_GET_PAGE_FAILURE", async () => {
        await _getPage()
        sinon.assert.calledWith(
          stubs.receiveGetPageFailure,
          { error, page }
        )
        sinon.assert.calledWith(
          dispatch,
          stubs.receiveGetPageFailure.returnValues[0]
        )
      })
    })
  })
})
