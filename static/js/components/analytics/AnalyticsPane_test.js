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
    sandbox = sinon.sandbox.create()
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
    for (const prop of ["analyticsData", "currentTime"]) {
      assert.equal(table.prop(prop), props[prop])
    }
  })
})
