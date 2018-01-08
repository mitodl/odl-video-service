// @flow
import sinon from "sinon"
import ga from "react-ga"
import { assert } from "chai"

import { sendGAEvent } from "./google_analytics"

describe("Google Analytics", () => {
  let event, sandbox

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    event = sandbox.stub(ga, "event")
  })

  afterEach(() => sandbox.restore())

  describe("sendGAEvent", () => {
    it("should send an event to GA properly", () => {
      sendGAEvent("category", "action", "label", 1)
      assert(
        event.calledWith({
          category: "category",
          action:   "action",
          label:    "label",
          value:    1
        }),
        "should be called with the right values"
      )
    })

    it("should not include `value` if it is undefined", () => {
      sendGAEvent("category", "action", "label")
      assert(
        event.calledWith({
          category: "category",
          action:   "action",
          label:    "label"
        }),
        "there should not be a value for 'value'"
      )
    })

    it("should not include `value` if it is not a valid number", () => {
      // $FlowFixMe
      sendGAEvent("category", "action", "label", "hello")
      assert(
        event.calledWith({
          category: "category",
          action:   "action",
          label:    "label"
        }),
        "there should not be a value for 'value'"
      )
    })

    it("`value` string should be converted to a valid integer if possible", () => {
      // $FlowFixMe
      sendGAEvent("category", "action", "label", "45.5")
      assert(
        event.calledWith({
          category: "category",
          action:   "action",
          label:    "label",
          value:    46
        }),
        "there should not be a value for 'value'"
      )
    })

    it("`value` float should be converted to a valid integer if possible", () => {
      sendGAEvent("category", "action", "label", 45.5)
      assert(
        event.calledWith({
          category: "category",
          action:   "action",
          label:    "label",
          value:    46
        }),
        "there should not be a value for 'value'"
      )
    })
  })
})
