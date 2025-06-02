// @flow
import { assert } from "chai"
import sinon from "sinon"
import configureTestStore from "redux-asserts"
import * as api from "../lib/api"
import { actions } from "../actions"
import rootReducer from "../reducers"

describe("Users reducer", () => {
  let sandbox, store, getStub, listenForActions

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    getStub = sandbox.stub(api, "getUsers").returns(
      Promise.resolve({
        users: [
          { id: 1, username: "user1", email: "user1@example.com" },
          { id: 2, username: "user2", email: "user2@example.com" }
        ]
      })
    )
  })

  afterEach(() => {
    sandbox.restore()
  })

  it("should handle API request for users list", async () => {
    const expectedActions = [
      actions.usersList.get.requestType,
      actions.usersList.get.successType
    ]

    await listenForActions(expectedActions, () => {
      return store.dispatch(actions.usersList.get())
    })

    assert.isTrue(getStub.calledOnce)

    const state = store.getState().usersList
    assert.isFalse(state.processing)
    assert.equal(state.error, null)
    assert.deepEqual(state.data, {
      users: [
        { id: 1, username: "user1", email: "user1@example.com" },
        { id: 2, username: "user2", email: "user2@example.com" }
      ]
    })
  })

  it("should handle API error", async () => {
    getStub.returns(Promise.reject(new Error("Network error")))

    const expectedActions = [
      actions.usersList.get.requestType,
      actions.usersList.get.failureType
    ]

    // The dispatch itself should throw an error, not the listenForActions
    await listenForActions(expectedActions, () => {
      return store.dispatch(actions.usersList.get()).catch(() => {
        return Promise.resolve()
      })
    })

    // Verify error state instead of trying to catch the error
    const state = store.getState().usersList
    assert.isFalse(state.processing)
    assert.instanceOf(state.error, Error)
    assert.equal(state.error.message, "Network error")
  })
})
