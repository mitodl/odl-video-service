import React from "react"
import { assert } from "chai"
import { mount } from "enzyme"

import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"
import AnalyticsChart from "./AnalyticsChart"

describe("AnalyticsChart", () => {
  let analyticsData, props

  beforeEach(() => {
    analyticsData = makeVideoAnalyticsData(10)
    props = { analyticsData }
  })

  const renderChart = () => {
    const wrapper = mount(<AnalyticsChart {...props} />)
    wrapper.update()
    return wrapper
  }

  it("renders", () => {
    const wrapper = renderChart()
    assert.isTrue(wrapper.exists())
  })
})
