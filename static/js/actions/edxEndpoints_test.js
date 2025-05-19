// @flow
import { assert } from "chai"
import sinon from "sinon"
import configureTestStore from "redux-asserts"

import rootReducer from "../reducers"
import { actions } from "../actions"
import * as api from "../lib/api"
import { makeEdxEndpointList } from "../factories/edxEndpoints"
import * as edxEndpointActions from "./edxEndpoints"

describe("edxEndpoints actions", () => {
  let sandbox, store, dispatchThen

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    dispatchThen = store.createDispatchThen(state => state.edxEndpoints)
  })

  afterEach(() => {
    sandbox.restore()
  })

  describe("getEndpoints", () => {
    it("fetches endpoints", async () => {
      const endpoints = makeEdxEndpointList()
      const getEndpointsStub = sandbox
        .stub(api, "getEdxEndpoints")
        .returns(Promise.resolve( endpoints ))

      const { data } = await dispatchThen(actions.edxEndpoints.getEndpoints(), [
        edxEndpointActions.constants.REQUEST_GET_ENDPOINTS,
        edxEndpointActions.constants.RECEIVE_GET_ENDPOINTS_SUCCESS
      ])
      assert.deepEqual(data, endpoints)
      sinon.assert.calledWith(getEndpointsStub)
    })

    it("handles errors", async () => {
      const errorMessage = "Error fetching endpoints"
      sandbox
        .stub(api, "getEdxEndpoints")
        .returns(Promise.reject(new Error(errorMessage)))

      const { error } = await dispatchThen(actions.edxEndpoints.getEndpoints(), [
        edxEndpointActions.constants.REQUEST_GET_ENDPOINTS,
        edxEndpointActions.constants.RECEIVE_GET_ENDPOINTS_FAILURE
      ])
      assert.equal(error.message, errorMessage)
    })
  })
})
