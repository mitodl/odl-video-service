// @flow
import { assert } from "chai"
import sinon from "sinon"
import configureTestStore from "redux-asserts"

import rootReducer from "../reducers"
import { actions } from "../actions"

describe("toast reducer", () => {
  let store, sandbox

  beforeEach(() => {
    store = configureTestStore(rootReducer)
    sandbox = sinon.createSandbox()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const getToastState = () => {
    return store.getState().toast
  }

  const _dispatchAddMessage = (...args) => {
    store.dispatch(actions.toast.addMessage(...args))
  }

  const _dispatchRemoveMessage = (...args) => {
    store.dispatch(actions.toast.removeMessage(...args))
  }

  it("has initial state", () => {
    const expectedInitialState = {
      messages: []
    }
    assert.deepEqual(getToastState(), expectedInitialState)
  })

  describe("ADD_MESSAGE", () => {
    it("adds message", async () => {
      assert.deepEqual(getToastState().messages, [])
      const message1 = { key: "1", content: "message1" }
      _dispatchAddMessage({ message: message1 })
      assert.deepEqual(getToastState().messages, [message1])
      const message2 = { key: "2", content: "message2" }
      _dispatchAddMessage({ message: message2 })
      assert.deepEqual(getToastState().messages, [message1, message2])
    })
  })

  describe("REMOVE_MESSAGE", () => {
    it("removes message", async () => {
      assert.deepEqual(getToastState().messages, [])
      const message1 = { key: "1", content: "message1" }
      _dispatchAddMessage({ message: message1 })
      assert.deepEqual(getToastState().messages, [message1])
      _dispatchRemoveMessage({ key: "baloney" })
      assert.deepEqual(getToastState().messages, [message1])
      _dispatchRemoveMessage({ key: message1.key })
      assert.deepEqual(getToastState().messages, [])
      _dispatchRemoveMessage({ key: "ham" })
      assert.deepEqual(getToastState().messages, [])
    })
  })
})
