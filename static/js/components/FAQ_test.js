// @flow
/* global SETTINGS:false */
import React from "react"
import sinon from "sinon"
import { shallow } from "enzyme"
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
    shallow(
      <FAQ
        FAQVisibility={FAQVisibility}
        toggleFAQVisibility={toggleFAQVisibility}
      />
    )

  it("shows the appropriate FAQ sections to the user", () => {
    const wrapper = renderFAQs()
    const sections = wrapper
      .find(".mdc-typography--subheading")
      .map(wrapper => wrapper.at(0).text())
    assert.deepEqual(sections, Object.keys(sectionFAQs))
  })

  it("shows the appropriate FAQs to the user", () => {
    const wrapper = renderFAQs()
    const questions = wrapper.find(".show-hide-question").map(wrapper =>
      wrapper
        .find("div")
        .at(1)
        .text()
    )
    assert.deepEqual(
      questions.slice(0, -1),
      _.flatMap(sectionFAQs, item => Object.keys(item))
    )
  })

  it("calls the toggleFAQVisibility callback when a question title is clicked", () => {
    const wrapper = renderFAQs()
    wrapper
      .find(".show-hide-question")
      .at(0)
      .simulate("click")
    assert(toggleFAQVisibility.called)
  })

  it("checks FAQVisibility to see if a question should be open", () => {
    Object.entries(sectionFAQs).forEach(section => {
      Object.entries(section[1]).forEach(([question, answer]) => {
        [true, false].forEach(visibility => {
          FAQVisibility.set(question, visibility)
          const wrapper = renderFAQs()
          if (visibility) {
            assert.equal(wrapper.find(".answer").text(), shallow(answer).text())
          } else {
            assert.lengthOf(wrapper.find(".answer"), 0)
          }
        })
      })
    })
  })
})
