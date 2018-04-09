import React from "react"
import { assert } from "chai"
import { mount } from "enzyme"

import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"
import AnalyticsTable from "./AnalyticsTable"

describe("AnalyticsTable", () => {
  let analyticsData, props

  beforeEach(() => {
    analyticsData = makeVideoAnalyticsData(10)
    props = { analyticsData }
  })

  const renderTable = () => {
    const wrapper = mount(<AnalyticsTable {...props} />)
    wrapper.update()
    return wrapper
  }

  it("renders", () => {
    const wrapper = renderTable()
    assert.isTrue(wrapper.exists())
  })
})
