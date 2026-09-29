import configureTestStore from "redux-asserts"
import { assert } from "chai"
import sinon from "sinon"

import rootReducer from "../reducers"
import { actions } from "../actions"
import { makeCollection } from "../factories/collection"
import * as api from "../lib/api"
import type { Collection } from "../types/collectionTypes"
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

describe("collections endpoints", () => {
  let store, dispatchThen, collections: Array<Collection>, sandbox: Sandbox

  beforeEach(() => {
    store = configureTestStore(rootReducer)
    sandbox = sinon.createSandbox()
    dispatchThen = store.createDispatchThen()

    collections = [makeCollection(), makeCollection()]
  })

  afterEach(() => {
    sandbox.restore()
  })

  it("adds a new collection to the beginning of the list", async () => {
    sandbox
      .stub(api, "getCollections")
      .returns(Promise.resolve({ results: collections }))
    let state = await dispatchThen(actions.collectionsList.get(), [
      actionTypes(actions.collectionsList.get).requestType,
      actionTypes(actions.collectionsList.get).successType
    ])

    assert.deepEqual(state.collectionsList.data.results, collections)

    const newCollection = makeCollection()
    sandbox
      .stub(api, "createCollection")
      .returns(Promise.resolve(newCollection))
    state = await dispatchThen(actions.collectionsList.post(newCollection), [
      actionTypes(actions.collectionsList.post).requestType,
      actionTypes(actions.collectionsList.post).successType
    ])
    assert.deepEqual(state.collectionsList.data.results, [
      newCollection,
      ...collections
    ])
  })
})
