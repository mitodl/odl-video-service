import React from "react"
import { assert } from "chai"
import { shallow } from "enzyme"
import sinon from "sinon"

import AnalyticsPane from "./AnalyticsPane"

import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"
import { makeVideo } from "../../factories/video"

describe("AnalyticsPane", () => {
  let props, sandbox

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    props = {
      analyticsData: makeVideoAnalyticsData(),
      video:         makeVideo(),
      currentTime:   42,
      duration:      42 * 60,
      setVideoTime:  sandbox.spy()
    }
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = extraProps => {
    return shallow(<AnalyticsPane {...{ ...props, ...extraProps }} />)
  }

  it("renders chart", () => {
    const wrapper = renderComponent()
    const chart = wrapper.find("AnalyticsChart")
    // eslint-disable-next-line no-unused-vars
    for (const prop of ["analyticsData", "currentTime", "duration"]) {
      assert.equal(chart.prop(prop), props[prop])
    }
  })

  it("renders progress slider", () => {
    const wrapper = renderComponent()
    const slider = wrapper.find("ProgressSlider")
    assert.equal(slider.prop("value"), props.currentTime / props.duration)
  })

  it("renders table", () => {
    const wrapper = renderComponent()
    const table = wrapper.find("AnalyticsInfoTable")
    // eslint-disable-next-line no-unused-vars
    for (const prop of ["analyticsData", "currentTime"]) {
      assert.equal(table.prop(prop), props[prop])
    }
  })
})
