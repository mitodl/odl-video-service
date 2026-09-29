import { assert } from "chai"
import sinon from "sinon"
import { INITIAL_STATE } from "redux-hammock/constants"
import configureTestStore from "redux-asserts"
import * as api from "../lib/api"

import rootReducer from "../reducers"
import { actions } from "../actions"
import { makeVideo } from "../factories/video"
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

describe("videos endpoint", () => {
  let store, sandbox: Sandbox, dispatchThen, getVideoStub, updateVideoStub

  beforeEach(() => {
    store = configureTestStore(rootReducer)
    dispatchThen = store.createDispatchThen()
    sandbox = sinon.createSandbox()
    getVideoStub = sandbox.stub(api, "getVideo").throws()
    updateVideoStub = sandbox.stub(api, "updateVideo").throws()
  })

  afterEach(() => {
    sandbox.restore()
  })

  it("should have some initial state", () => {
    assert.deepEqual(store.getState().videos, {
      ...INITIAL_STATE,
      data: new Map()
    })
  })

  it("should get videos", async () => {
    const video = makeVideo()
    getVideoStub.returns(Promise.resolve(video))
    await dispatchThen(actions.videos.get(video.key), [
      actionTypes(actions.videos.get).requestType,
      actionTypes(actions.videos.get).successType
    ])
    assert.deepEqual(store.getState().videos.data.get(video.key), video)
    sinon.assert.calledWith(getVideoStub, video.key)
  })

  it("should patch videos", async () => {
    const video = makeVideo()
    const payload = {
      title: "new title"
    }
    const videoWithDifferentTitle = { ...video, ...payload }
    updateVideoStub.returns(Promise.resolve(videoWithDifferentTitle))
    await dispatchThen(actions.videos.patch(video.key, payload), [
      actionTypes(actions.videos.patch).requestType,
      actionTypes(actions.videos.patch).successType
    ])
    assert.deepEqual(
      store.getState().videos.data.get(video.key),
      videoWithDifferentTitle
    )
    sinon.assert.calledWith(updateVideoStub, video.key, payload)
  })
})
