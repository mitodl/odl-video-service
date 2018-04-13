// @flow
import React from "react"
import sinon from "sinon"
import { shallow } from "enzyme"
import { assert } from "chai"

import Paginator from "./Paginator"

describe("Paginator", () => {
  let sandbox,

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (props = {}) => {
    return shallow(<Paginator {...props} />)
  }

  it("shows total number of items", () => {
    assert.equal(true, false)
  })

  it("shows current range", () => {
    assert.equal(true, false)
  })

  it("shows prev button", () => {
    assert.equal(true, false)
  })

  it("shows next button", () => {
    assert.equal(true, false)
  })

  describe("when in the middle of the full range", () => {
    it("triggers onNext when next button clicked", () => {
      assert.equal(true, false)
    })

    it("triggers onPrev when prev button clicked", () => {
      assert.equal(true, false)
    })
  })

  describe("when at the end of the full range", () => {
    it("disables the next button", () => {
      assert.equal(true, false)
    })
  })

  describe("when at the beginning of the full range", () => {
    it("disables the prev button", () => {
      assert.equal(true, false)
    })
  })
})
