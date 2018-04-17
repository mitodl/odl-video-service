// @flow
import React from "react"
import sinon from "sinon"
import { shallow } from "enzyme"
import { assert } from "chai"

import Paginator from "./Paginator"

describe("Paginator", () => {
  let sandbox, stubs, props

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    stubs = {
      onClickNext: sandbox.spy(),
      onClickPrev: sandbox.spy(),
    }
    props = {
      currentPage: 42,
      totalPages:  4242,
      onClickNext: stubs.onClickNext,
      onClickPrev: stubs.onClickPrev,
    }
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (overrides = {}) => {
    return shallow(<Paginator {...props} {...overrides} />)
  }

  it("shows current page", () => {
    const wrapper = renderComponent()
    assert.equal(
      wrapper.find('.paginator-current-page').text(), 
      props.currentPage,
    )
  })

  it("shows total pages", () => {
    const wrapper = renderComponent()
    assert.equal(
      wrapper.find('.paginator-total-pages').text(), 
      props.totalPages,
    )
  })

  describe("when in the middle of the full range", () => {

    beforeEach(() => {
      props = {
        ...props,
        currentPage: 2,
        totalPages:  3
      }
    })

    it("triggers onClickNext when next button clicked", () => {
      const wrapper = renderComponent()
      sinon.assert.notCalled(stubs.onClickNext)
      wrapper.find('.paginator-next-button').simulate('click')
      sinon.assert.called(stubs.onClickNext)
    })

    it("triggers onClickPrev when prev button clicked", () => {
      const wrapper = renderComponent()
      sinon.assert.notCalled(stubs.onClickPrev)
      wrapper.find('.paginator-prev-button').simulate('click')
      sinon.assert.called(stubs.onClickPrev)
    })
  })

  describe("when at the end of the full range", () => {
    beforeEach(() => {
      props = {
        ...props,
        currentPage: 3,
        totalPages:  3
      }
    })

    it("disables the next button", () => {
      const wrapper = renderComponent()
      sinon.assert.notCalled(stubs.onClickNext)
      const nextButton = wrapper.find('.paginator-next-button')
      nextButton.simulate('click')
      sinon.assert.notCalled(stubs.onClickNext)
      assert.isTrue(nextButton.hasClass('disabled'))
    })
  })

  describe("when at the beginning of the full range", () => {
    beforeEach(() => {
      props = {
        ...props,
        currentPage: 1,
        totalPages:  3
      }
    })

    it("disables the prev button", () => {
      const wrapper = renderComponent()
      sinon.assert.notCalled(stubs.onClickPrev)
      const prevButton = wrapper.find('.paginator-prev-button')
      prevButton.simulate('click')
      sinon.assert.notCalled(stubs.onClickPrev)
      assert.isTrue(prevButton.hasClass('disabled'))
    })
  })
})
