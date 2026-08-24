import React from "react"
import { assert } from "chai"
import { render } from "@testing-library/react"

import AnalyticsInfoTable from "./AnalyticsInfoTable"

import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"

describe("AnalyticsInfoTable", () => {
  let props, fixtures, container

  beforeEach(() => {
    fixtures = {
      analyticsData: {
        multiChannel:  makeVideoAnalyticsData(10),
        singleChannel: makeVideoAnalyticsData(10, false)
      }
    }
    props = {
      analyticsData:      fixtures.analyticsData.multiChannel,
      currentTime:        342,
      getColorForChannel: () => "ecru"
    }
  })

  const renderComponent = extraProps => {
    return render(<AnalyticsInfoTable {...{ ...props, ...extraProps }} />)
  }

  describe("header", () => {
    beforeEach(() => {
      container = renderComponent().container
    })

    it("renders time header", () => {
      assert.equal(container.querySelector("th.time").textContent, "time")
    })

    it("renders total views header", () => {
      assert.equal(
        container.querySelector("th.total-views").textContent,
        "total views"
      )
    })

    describe("when multichannel", () => {
      it("renders channel name headers", () => {
        const channelEls = container.querySelectorAll("th.channel")
        assert.equal(
          channelEls.length,
          fixtures.analyticsData.multiChannel.channels.length
        )
        assert.deepEqual(
          Array.from(channelEls)
            .map(channelEl => channelEl.textContent)
            .sort(),
          fixtures.analyticsData.multiChannel.channels.sort()
        )
      })
    })

    describe("when not multichannel", () => {
      beforeEach(() => {
        container = renderComponent({
          analyticsData: fixtures.analyticsData.singleChannel
        }).container
      })

      it("does renders total views label as views", () => {
        assert.equal(
          container.querySelector("th.total-views").textContent,
          "views"
        )
      })

      it("does not render channel names", () => {
        assert.equal(container.querySelectorAll("th.channel").length, 0)
      })
    })
  })

  describe("time row", () => {
    beforeEach(() => {
      container = renderComponent().container
    })

    it("renders time", () => {
      const minute = Math.floor(props.currentTime / 60)
      const remainder = Math.floor(props.currentTime - 60 * minute)
      const pad = (num, size) => String(num).padStart(size, "0")
      const expectedTime = `${pad(minute, 2)}:${pad(remainder, 2)}`
      assert.equal(container.querySelector("td.time").textContent, expectedTime)
    })

    describe("when multichannel", () => {
      it("renders total views", () => {
        assert.equal(
          container.querySelector("td.total-views").textContent,
          "28"
        )
      })

      it("renders channel views", () => {
        const viewsByChannel = {}
        fixtures.analyticsData.multiChannel.channels.forEach(channel => {
          const td = container.querySelector(`td.channel.${channel}`)
          viewsByChannel[channel] = td.textContent
        })
        assert.deepEqual(viewsByChannel, {
          channel1: "4 (14.3%)",
          channel2: "7 (25.0%)",
          channel3: "8 (28.6%)",
          channel4: "9 (32.1%)"
        })
      })
    })

    describe("when not multichannel", () => {
      beforeEach(() => {
        container = renderComponent({
          analyticsData: fixtures.analyticsData.singleChannel
        }).container
      })

      it("renders total views", () => {
        assert.equal(container.querySelector("td.total-views").textContent, "4")
      })

      it("does not render channel views", () => {
        assert.equal(container.querySelectorAll("td.channel").length, 0)
      })
    })
  })
})
