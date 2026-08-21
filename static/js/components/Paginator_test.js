// @flow
import React from "react"
import sinon from "sinon"
import { render, fireEvent } from "@testing-library/react"
import { assert } from "chai"

import Paginator from "./Paginator"

describe("Paginator", () => {
  let sandbox, stubs, props

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    stubs = {
      onClickNext: sandbox.spy(),
      onClickPrev: sandbox.spy()
    }
    props = {
      currentPage: 42,
      totalPages:  4242,
      onClickNext: stubs.onClickNext,
      onClickPrev: stubs.onClickPrev
    }
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (overrides = {}) => {
    return render(<Paginator {...props} {...overrides} />)
  }

  it("shows current page", () => {
    const { container } = renderComponent()
    assert.equal(
      container.querySelector(".paginator-current-page").textContent,
      props.currentPage
    )
  })

  it("shows total pages", () => {
    const { container } = renderComponent()
    assert.equal(
      container.querySelector(".paginator-total-pages").textContent,
      props.totalPages
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
      const { container } = renderComponent()
      sinon.assert.notCalled(stubs.onClickNext)
      fireEvent.click(container.querySelector(".paginator-next-button"))
      sinon.assert.called(stubs.onClickNext)
    })

    it("triggers onClickPrev when prev button clicked", () => {
      const { container } = renderComponent()
      sinon.assert.notCalled(stubs.onClickPrev)
      fireEvent.click(container.querySelector(".paginator-prev-button"))
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
      const { container } = renderComponent()
      sinon.assert.notCalled(stubs.onClickNext)
      const nextButton = container.querySelector(".paginator-next-button")
      fireEvent.click(nextButton)
      sinon.assert.notCalled(stubs.onClickNext)
      assert.isTrue(nextButton.classList.contains("disabled"))
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
      const { container } = renderComponent()
      sinon.assert.notCalled(stubs.onClickPrev)
      const prevButton = container.querySelector(".paginator-prev-button")
      fireEvent.click(prevButton)
      sinon.assert.notCalled(stubs.onClickPrev)
      assert.isTrue(prevButton.classList.contains("disabled"))
    })
  })
})
