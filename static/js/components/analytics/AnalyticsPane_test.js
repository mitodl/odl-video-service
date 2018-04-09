// @flow
import React from "react"
import sinon from "sinon"
import { mount } from "enzyme"
import { assert } from "chai"

import AnalyticsPane from "./AnalyticsPane"
import { makeVideo } from "../../factories/video"
import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"

describe("AnalyticsPane", () => {
  let sandbox, video, analyticsData

  const CSS_NS = "analytics-pane"

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    video = makeVideo()
    analyticsData = makeVideoAnalyticsData
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = () => {
    const wrapper = mount(
      <AnalyticsPane video={video} analyticsData={analyticsData} />
    )
    wrapper.update()
    return wrapper
  }

  describe("header", () => {
    it("shows header", () => {
      const wrapper = renderComponent()
      assert.isTrue(wrapper.find(`.${CSS_NS}-header`).exists())
    })

    it("shows video title", () => {
      const wrapper = renderComponent()
      assert.isTrue(wrapper.find(`.${CSS_NS}-video-title`).exists())
    })

    it("shows video link", () => {
      const wrapper = renderComponent()
      assert.isTrue(wrapper.find(`.${CSS_NS}-video-link`).exists())
    })
  })

  describe("body", () => {
    describe("when analyticsData is populated", () => {
      let mockFormattedAnalyticsData, formatAnalyticsDataStub

      beforeEach(() => {
        analyticsData = makeVideoAnalyticsData(10)
        mockFormattedAnalyticsData = makeVideoAnalyticsData(10)
        formatAnalyticsDataStub = sandbox
          .stub(AnalyticsPane.prototype, "formatAnalyticsData")
          .returns(mockFormattedAnalyticsData)
      })

      it("has graph and table tabs", () => {
        const wrapper = renderComponent()
        const tabs = wrapper.find("Tab")
        const tabTitles = tabs.map(tab => tab.text())
        assert.deepEqual(tabTitles.concat().sort(), ["Graph", "Table"])
      })

      it("shows graph tab by default with formatted data", () => {
        const wrapper = renderComponent()
        const chart = wrapper.find("AnalyticsChart")
        assert.equal(chart.length, 1)
        assert(
          formatAnalyticsDataStub.calledWith(wrapper.prop("analyticsData"))
        )
        assert.equal(chart.prop("analyticsData"), mockFormattedAnalyticsData)
        assert.equal(wrapper.find("AnalyticsTable").length, 0)
      })

      it("shows table tab if active with formatted data", () => {
        const wrapper = renderComponent()
        wrapper.setState({ activeTabIndex: 1 })
        const table = wrapper.find("AnalyticsTable")
        assert.equal(table.length, 1)
        assert(
          formatAnalyticsDataStub.calledWith(wrapper.prop("analyticsData"))
        )
        assert.equal(table.prop("analyticsData"), mockFormattedAnalyticsData)
        assert.equal(wrapper.find("AnalyticsChart").length, 0)
      })
    })

    describe("formatAnalyticsData", () => {
      it("interpolates times", () => {
        const analyticsData = {
          times:          [0, 2, 4],
          channels:       ["channel0", "channel3"],
          views_at_times: {
            "0": {
              channel0: 1,
              channel3: 3
            },
            "2": {
              channel0: 7
            },
            "4": {
              channel3: 5
            }
          }
        }
        const wrapper = renderComponent()
        const actual = wrapper.instance().formatAnalyticsData(analyticsData)
        const expected = {
          ...analyticsData,
          times: [0, 1, 2, 3, 4]
        }
        assert.deepEqual(actual, expected)
      })
    })

    describe("when analyticsData is empty", () => {
      beforeEach(() => {
        sandbox = sinon.sandbox.create()
        sandbox
          .stub(AnalyticsPane.prototype, "analyticsDataIsEmpty")
          .returns(true)
      })

      it("renders empty data message", () => {
        const wrapper = renderComponent()
        assert.equal(wrapper.find(`.${CSS_NS}-empty-data-message`).length, 1)
        assert.equal(wrapper.find("AnalyticsChart").length, 0)
        assert.equal(wrapper.find("AnalyticsTable").length, 0)
      })
    })
  })

  describe("analyticsDataIsEmpty", () => {
    [[{}, true], [{ times: [] }, true], [{ times: [1] }, false]].forEach(
      testDef => {
        const [analyticsData, expected] = testDef
        it(
          `should return ${String(expected)} when analyticsData is ` +
            `${JSON.stringify(analyticsData)}`,
          () => {
            const actual = AnalyticsPane.prototype.analyticsDataIsEmpty(
              analyticsData
            )
            assert.equal(actual, expected)
          }
        )
      }
    )
  })
})
