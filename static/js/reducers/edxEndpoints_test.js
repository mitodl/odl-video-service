// @flow
import { assert } from "chai"

import edxEndpoints from "../reducers/edxEndpoints"
import * as api from "../lib/api"
import { actions } from "../actions"
import { makeEdxEndpointList } from "../factories/edxEndpoints"
import * as sinon from "sinon"
import configureTestStore from "redux-asserts"

describe("edxEndpoints reducer", () => {
  let sandbox, store, dispatchThen, getEdxEndpointsStub, endpointList

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    endpointList = makeEdxEndpointList()
    getEdxEndpointsStub = sandbox
      .stub(api, "getEdxEndpoints")
      .returns(Promise.resolve({ results: endpointList }))
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
    const { data } = await dispatchThen(actions.edxEndpoints.getEndpoints())
    assert.deepEqual(data, endpointList)
    sinon.assert.calledWith(getEdxEndpointsStub)
  })
})
