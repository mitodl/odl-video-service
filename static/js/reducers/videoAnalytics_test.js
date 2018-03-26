// @flow
import { assert } from "chai"
import sinon from "sinon"
import { INITIAL_STATE } from "redux-hammock/constants"
import configureTestStore from "redux-asserts"
import * as api from "../lib/api"

import rootReducer from "../reducers"
import { actions } from "../actions"

describe("videoAnalytics endpoint", () => {
  let store, sandbox, dispatchThen, getVideoAnalyticsStub

  beforeEach(() => {
    store = configureTestStore(rootReducer)
    dispatchThen = store.createDispatchThen()
    sandbox = sinon.sandbox.create()
    getVideoAnalyticsStub = sandbox.stub(api, "getVideoAnalytics").throws()
  })

  afterEach(() => {
    sandbox.restore()
  })

  it("should have some initial state", () => {
    assert.deepEqual(store.getState().videoAnalytics, {
      ...INITIAL_STATE,
      data: new Map()
    })
  })

  it("should get videoAnalytics", async () => {
    const videoKey = "someVideoKey"
    const mockResponse = { key: videoKey, data: { some: "data" } }
    getVideoAnalyticsStub.returns(Promise.resolve(mockResponse))
    await dispatchThen(actions.videoAnalytics.get(videoKey), [
      actions.videoAnalytics.get.requestType,
      actions.videoAnalytics.get.successType
    ])
    sinon.assert.calledWith(getVideoAnalyticsStub, videoKey)
  })
})
