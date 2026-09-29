import { assert } from "chai"
import sinon from "sinon"
import { INITIAL_STATE } from "redux-hammock/constants"
import configureTestStore from "redux-asserts"
import * as api from "../lib/api"

import rootReducer from "../reducers"
import { actions } from "../actions"
import type { Sandbox } from "../types/sinonTypes"

/*
 * redux-hammock hangs the action-type constants off each derived thunk
 * creator, but the RestActions signature in actions/index.ts describes those
 * creators as bare callables, so the constants need a narrowing here. Local
 * on purpose: actions/index.ts is a source file this conversion may not edit.
 */
type RestActionTypes = {
  requestType: string
  successType: string
  failureType: string
}
const actionTypes = (creator: unknown) => creator as RestActionTypes

describe("videoAnalytics endpoint", () => {
  let store, sandbox: Sandbox, dispatchThen, getVideoAnalyticsStub

  beforeEach(() => {
    store = configureTestStore(rootReducer)
    dispatchThen = store.createDispatchThen()
    sandbox = sinon.createSandbox()
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
      actionTypes(actions.videoAnalytics.get).requestType,
      actionTypes(actions.videoAnalytics.get).successType
    ])
    sinon.assert.calledWith(getVideoAnalyticsStub, videoKey)
  })
})
