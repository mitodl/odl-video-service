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

  describe("when multichannel", () => {
    it("shows total views with percentage", () => {
      analyticsData.is_multichannel = true 
      const wrapper = renderTable()
      const row = wrapper.find('tbody > tr').at(0)
      assert.equal(
        row.find('td.views').length,
        analyticsData.channels.length + 1
      )
      assert.equal(
        row.find('.percent').length,
        analyticsData.channels.length + 1
      )
    })
  })

  describe("when not multichannel", () => {
    it("does not show total views with percentage", () => {
      analyticsData.is_multichannel = false
      const wrapper = renderTable()
      const row = wrapper.find('tbody > tr').at(0)
      assert.equal(row.find('td.views').length, 1)
      assert.equal(row.find('.percent').length, 0)
    })
  })

})
