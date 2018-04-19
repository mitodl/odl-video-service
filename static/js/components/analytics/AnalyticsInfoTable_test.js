import React from "react"
import { assert } from "chai"
import { shallow } from "enzyme"

import AnalyticsInfoTable from "./AnalyticsInfoTable"

import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"


describe("AnalyticsInfoTable", () => {
  let props, fixtures, wrapper

  beforeEach(() => {
    fixtures = {
      analyticsData: {
        multiChannel:  makeVideoAnalyticsData(10),
        singleChannel: makeVideoAnalyticsData(10, false),
      }
    }
    props = {
      analyticsData:      fixtures.analyticsData.multiChannel,
      currentTime:        342,
      getColorForChannel: () => 'ecru',
    }
  })

  const renderComponent = ((extraProps) => {
    return shallow(
      <AnalyticsInfoTable {...{...props, ...extraProps}} />
    )
  })

  describe("header", () => {
    beforeEach(() => {
      wrapper = renderComponent()
    })

    it("renders time header", () => {
      assert.equal(wrapper.find('th.time').text(), 'time')
    })

    it("renders total views header", () => {
      assert.equal(wrapper.find('th.total-views').text(), 'total views')
    })

    describe("when multichannel", () => {
      it("renders channel name headers", () => {
        const analyticsData = wrapper.instance().props.analyticsData
        const channelEls = wrapper.find('th.channel')
        assert.equal(channelEls.length, analyticsData.channels.length)
        assert.deepEqual(
          channelEls.map((channelEl) => channelEl.text()).sort(),
          analyticsData.channels.sort()
        )
      })
    })

    describe("when not multichannel", () => {
      beforeEach(() => {
        wrapper = renderComponent({
          analyticsData: fixtures.analyticsData.singleChannel
        })
      })

      it("does renders total views label as views", () => {
        const totalViewsTh = wrapper.find('th.total-views')
        assert.equal(totalViewsTh.text(), 'views')
      })

      it("does not render channel names", () => {
        const channelEls = wrapper.find('th.channel')
        assert.equal(channelEls.length, 0)
      })
    })
  })

  describe("time row", () => {
    beforeEach(() => {
      wrapper = renderComponent()
    })

    it("renders time", () => {
      const timeTd = wrapper.find('td.time')
      assert.equal(
        timeTd.text(),
        wrapper.instance().secondsToTimeStr(props.currentTime)
      )
    })

    describe("when multichannel", () => {
      it("renders total views", () => {
        const totalViewsTd = wrapper.find('td.total-views')
        assert.equal(totalViewsTd.text(), 28)
      })

      it("renders channel views", () => {
        const channelViewsTds = wrapper.find('td.channel')
        const viewsByChannel = {}
        channelViewsTds.forEach((td) => {
          viewsByChannel[td.key()] = td.text()
        })
        assert.deepEqual(
          viewsByChannel,
          {
            channel1: "4 (14.3%)",
            channel2: "7 (25.0%)",
            channel3: "8 (28.6%)",
            channel4: "9 (32.1%)",
          }
        )
      })
    })

    describe("when not multichannel", () => {
      beforeEach(() => {
        wrapper = renderComponent({
          analyticsData: fixtures.analyticsData.singleChannel
        })
      })

      it("renders total views", () => {
        const totalViewsTd = wrapper.find('td.total-views')
        assert.equal(totalViewsTd.text(), 4)
      })

      it("does not render channel views", () => {
        const channelTds = wrapper.find('td.channel')
        assert.equal(channelTds.length, 0)
      })
    })
  })
})
