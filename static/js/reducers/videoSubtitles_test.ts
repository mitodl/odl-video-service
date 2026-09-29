import { assert } from "chai"
import sinon from "sinon"
import { INITIAL_STATE } from "redux-hammock/constants"
import configureTestStore from "redux-asserts"
import * as api from "../lib/api"

import rootReducer from "../reducers"
import { actions } from "../actions"
import { makeVideoSubtitle } from "../factories/video"
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
  let store,
    sandbox: Sandbox,
    dispatchThen,
    createSubtitleStub,
    deleteSubtitleStub

  beforeEach(() => {
    store = configureTestStore(rootReducer)
    dispatchThen = store.createDispatchThen()
    sandbox = sinon.createSandbox()
    createSubtitleStub = sandbox.stub(api, "createSubtitle").throws()
    deleteSubtitleStub = sandbox.stub(api, "deleteSubtitle").throws()
  })

  afterEach(() => {
    sandbox.restore()
  })

  it("should have some initial state", () => {
    assert.deepEqual(store.getState().videoSubtitles, {
      ...INITIAL_STATE,
      data: new Map()
    })
  })

  it("should create subtitles", async () => {
    const subtitle = makeVideoSubtitle()
    createSubtitleStub.returns(Promise.resolve(subtitle))
    const payload = new FormData()
    payload.append("collection_key", "fake-key")
    payload.append("video", "fake-key")
    // $FlowFixMe
    // FormData.append takes string | Blob; this passes an array of plain
    // objects on purpose, so the cast keeps the call exactly as it was.
    payload.append("file", [{ name: "foo", data: "" }] as unknown as Blob)
    await dispatchThen(actions.videoSubtitles.post(payload), [
      actionTypes(actions.videoSubtitles.post).requestType,
      actionTypes(actions.videoSubtitles.post).successType
    ])
    sinon.assert.calledWith(createSubtitleStub, payload)
  })

  it("should delete subtitles", async () => {
    const subtitle = makeVideoSubtitle()
    deleteSubtitleStub.returns(Promise.resolve({}))
    await dispatchThen(actions.videoSubtitles.delete(subtitle.id), [
      actionTypes(actions.videoSubtitles.delete).requestType,
      actionTypes(actions.videoSubtitles.delete).successType
    ])
    sinon.assert.calledWith(deleteSubtitleStub, subtitle.id)
  })
})
