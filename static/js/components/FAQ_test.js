// @flow
/* global SETTINGS:false */
import React from "react"
import sinon from "sinon"
import { render, screen, fireEvent, cleanup } from "@testing-library/react"
import { assert } from "chai"
import _ from "lodash"

import FAQ from "./FAQ"

import { sectionFAQs } from "../data/faqs"

describe("FAQ Component", () => {
  let FAQVisibility, toggleFAQVisibility
  beforeEach(() => {
    FAQVisibility = new Map()
    toggleFAQVisibility = sinon.stub()
  })

  const renderFAQs = () =>
    render(
      <FAQ
        FAQVisibility={FAQVisibility}
        toggleFAQVisibility={toggleFAQVisibility}
      />
    )

  it("shows the appropriate FAQ sections to the user", () => {
    renderFAQs()
    const sections = screen
      .getAllByRole("heading", { level: 3 })
      .map(heading => heading.textContent)
    assert.deepEqual(sections, Object.keys(sectionFAQs))
  })

  it("shows the appropriate FAQs to the user", () => {
    const { container } = renderFAQs()
    const questions = [
      ...container.querySelectorAll(".show-hide-question")
    ].map(el => el.querySelector("div").textContent)
    assert.deepEqual(
      questions.slice(0, -1),
      _.flatMap(sectionFAQs, item => Object.keys(item))
    )
  })

  it("calls the toggleFAQVisibility callback when a question title is clicked", () => {
    const { container } = renderFAQs()
    fireEvent.click(container.querySelectorAll(".show-hide-question")[0])
    // Pre-existing bug in FAQ.js: onClick={toggleFAQVisibility(question)}
    // invokes the callback during render, not on click, so
    // toggleFAQVisibility is already `.called` before this click ever
    // fires. This assertion has never actually verified that a click does
    // anything -- ported as-is rather than fixed or strengthened.
    assert(toggleFAQVisibility.called)
  })

  it("checks FAQVisibility to see if a question should be open", () => {
    Object.entries(sectionFAQs).forEach(section => {
      Object.entries(section[1]).forEach(([question, answer]) => {
        [true, false].forEach(visibility => {
          FAQVisibility.set(question, visibility)
          const { container } = renderFAQs()
          if (visibility) {
            const answers = container.querySelectorAll(".answer")
            assert.lengthOf(answers, 1)
            assert.equal(
              answers[0].textContent,
              render(answer).container.textContent
            )
          } else {
            assert.lengthOf(container.querySelectorAll(".answer"), 0)
          }
          cleanup()
        })
      })
    })
  })
})
