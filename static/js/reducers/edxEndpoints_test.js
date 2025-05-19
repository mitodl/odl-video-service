// @flow
import { assert } from "chai"

import edxEndpoints from "../reducers/edxEndpoints"
import * as api from "../lib/api"
import { actions } from "../actions"
import { makeEdxEndpointList } from "../factories/edxEndpoints"
import * as sinon from "sinon"
import configureTestStore from "redux-asserts"
import * as edxEndpointActions from "../actions/edxEndpoints"

describe("edxEndpoints reducer", () => {
  let sandbox, store, dispatchThen, getEdxEndpointsStub, endpointList

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    endpointList = makeEdxEndpointList()
    getEdxEndpointsStub = sandbox
      .stub(api, "getEdxEndpoints")
      .returns(Promise.resolve( endpointList ))
    store = configureTestStore(edxEndpoints)
    dispatchThen = store.createDispatchThen(state => state)
  })

  afterEach(() => {
    sandbox.restore()
  })

  it("should have initial state", () => {
    assert.deepEqual(store.getState(), {
      data:   null,
      error:  null,
      status: "INITIAL"
    })
  })

  it("should let you fetch edX endpoints", async () => {
    const { data } = await dispatchThen(actions.edxEndpoints.getEndpoints(), [
        edxEndpointActions.constants.REQUEST_GET_ENDPOINTS,
        edxEndpointActions.constants.RECEIVE_GET_ENDPOINTS_SUCCESS
      ])
    assert.deepEqual(data, endpointList)
    sinon.assert.calledWith(getEdxEndpointsStub)
  })
})
