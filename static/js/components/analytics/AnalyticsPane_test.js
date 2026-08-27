import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { render, waitFor } from "@testing-library/react"

import AnalyticsPane from "./AnalyticsPane"

import suppressVictoryKeyWarning from "../../testUtils/suppressVictoryKeyWarning"

import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"
import { makeVideo } from "../../factories/video"

describe("AnalyticsPane", () => {
  let props, sandbox

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    // AnalyticsChart mounts a real Victory chart whose VictoryAxis emits a
    // spurious React "unique key prop" warning; see the helper for why it
    // is filtered here and nowhere else.
    suppressVictoryKeyWarning(sandbox)
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
    return render(<AnalyticsPane {...{ ...props, ...extraProps }} />)
  }

  // AnalyticsChart measures its container via a 200ms setTimeout in
  // componentDidMount before it renders the Victory chart into
  // .chart-container. Waiting for that svg to appear -- in every test, not
  // just the one asserting on it -- makes sure the timer has already fired
  // before RTL's automatic cleanup() unmounts the tree. Otherwise the
  // pending setTimeout fires after unmount and calls setState on an
  // unmounted component.
  const waitForChart = container =>
    waitFor(() => {
      const svg = container.querySelector(".chart-container svg")
      assert.isNotNull(svg, "expected AnalyticsChart to render an svg")
      return svg
    })

  // Helper for the x-axis tick labels the chart actually draws. AnalyticsChart
  // gives VictoryAxis every entry in analyticsData.times as a tick value, but
  // its ConditionalLabel only renders a label for every fifth minute.
  const expectedTimeLabels = analyticsData =>
    analyticsData.times.filter(t => t % 5 === 0).map(t => `${t}m`)

  const timeAxisLabels = svg =>
    Array.from(svg.querySelectorAll("text"))
      .map(el => el.textContent)
      .filter(text => /^\d+m$/.test(text))

  it("renders chart from the analytics data", async () => {
    const { container } = renderComponent()
    const svg = await waitForChart(container)

    // One stacked bar per channel per minute -- derived from the props, so a
    // wrong analyticsData reaching AnalyticsChart changes this count.
    const { channels, times } = props.analyticsData
    assert.lengthOf(
      svg.querySelectorAll("g.chart-body path"),
      channels.length * times.length,
      "expected one bar per channel per time"
    )
    assert.deepEqual(
      timeAxisLabels(svg),
      expectedTimeLabels(props.analyticsData)
    )
    // Note: AnalyticsPane also passes `currentTime` to AnalyticsChart, but
    // AnalyticsChart omits it from everything it renders, so there is nothing
    // in this svg to assert it against. Its observable effects are covered by
    // the table and progress-slider tests below.
  })

  it("re-renders the chart when the analytics data changes shape", async () => {
    // Same assertions against a deliberately different dataset (one channel,
    // 6 minutes instead of four channels and 24), so the counts above can't
    // pass as constants that happen to match the default factory.
    const analyticsData = makeVideoAnalyticsData(6, false)
    const { container } = renderComponent({ analyticsData })
    const svg = await waitForChart(container)

    assert.lengthOf(svg.querySelectorAll("g.chart-body path"), 6)
    assert.deepEqual(timeAxisLabels(svg), ["0m", "5m"])
  })

  // Recovers the chart's x-axis domain maximum, in minutes, from the rendered
  // geometry. AnalyticsChart sets that domain to [0, duration / 60], and
  // nothing else in the svg records `duration`, so this is what makes the
  // duration reaching AnalyticsChart an assertion instead of an assumption.
  //
  // The horizontal axis line spans the full domain in pixels, and a tick for
  // minute t is drawn at x1 + (t / domainMax) * (x2 - x1). Both are read from
  // the DOM, so the pixel span itself (which jsdom reports without layout)
  // cancels out and only the domain is asserted on.
  const xAxisDomainMaxMinutes = svg => {
    const axisLine = Array.from(svg.querySelectorAll("line")).find(line => {
      const [x1, x2, y1, y2] = ["x1", "x2", "y1", "y2"].map(attr =>
        line.getAttribute(attr)
      )
      return y1 !== null && y1 === y2 && x1 !== x2
    })
    assert.isDefined(axisLine, "expected a horizontal x-axis line")
    const x1 = Number(axisLine.getAttribute("x1"))
    const x2 = Number(axisLine.getAttribute("x2"))

    const tickMinute = 5
    const tickX = Array.from(svg.querySelectorAll("text")).find(
      el => el.textContent === `${tickMinute}m`
    )
    assert.isDefined(tickX, `expected a ${tickMinute}m tick label`)

    return (tickMinute * (x2 - x1)) / (Number(tickX.getAttribute("x")) - x1)
  }

  it("scales the chart's x axis to the video duration", async () => {
    const { container } = renderComponent()
    const svg = await waitForChart(container)
    assert.closeTo(
      xAxisDomainMaxMinutes(svg),
      props.duration / 60,
      0.01,
      "expected the x axis to span the video duration in minutes"
    )
  })

  it("rescales the chart's x axis for a different duration", async () => {
    const duration = 10 * 60
    const { container } = renderComponent({ duration })
    const svg = await waitForChart(container)
    assert.closeTo(xAxisDomainMaxMinutes(svg), 10, 0.01)
  })

  it("renders progress slider", async () => {
    const { container } = renderComponent()
    await waitForChart(container)
    const progressEl = container.querySelector(".progress")
    assert.isNotNull(progressEl, "expected a .progress element to render")
    assert.equal(
      progressEl.style.width,
      `${(props.currentTime / props.duration) * 100}%`
    )
  })

  it("renders table", async () => {
    const { container } = renderComponent()
    await waitForChart(container)

    const minute = Math.floor(props.currentTime / 60)
    const viewsAtTime = props.analyticsData.views_at_times[minute] || {}
    const totalViews = Object.values(viewsAtTime).reduce(
      (sum, views) => sum + views,
      0
    )
    const remainder = Math.floor(props.currentTime - 60 * minute)
    const pad = (num, size) => String(num).padStart(size, "0")
    const expectedTime = `${pad(minute, 2)}:${pad(remainder, 2)}`

    const timeEl = container.querySelector("td.time")
    const totalViewsEl = container.querySelector("td.total-views")
    assert.isNotNull(timeEl, "expected a td.time element to render")
    assert.isNotNull(
      totalViewsEl,
      "expected a td.total-views element to render"
    )
    assert.equal(timeEl.textContent, expectedTime)
    assert.equal(totalViewsEl.textContent, String(totalViews))
  })
})
