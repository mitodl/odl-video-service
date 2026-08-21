import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { render, waitFor } from "@testing-library/react"

import AnalyticsPane from "./AnalyticsPane"

import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"
import { makeVideo } from "../../factories/video"

describe("AnalyticsPane", () => {
  let props, sandbox

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    // AnalyticsChart mounts a real Victory (0.27.2) chart. VictoryAxis's own
    // tick-rendering code omits a `key` prop on an array of children, which
    // React reports via console.error on every mount. Enzyme's shallow
    // rendering never mounted this child, so the defect -- which lives
    // entirely inside Victory, not in AnalyticsChart's usage of it or in
    // anything asserted below -- was never exercised before. The rendered
    // SVG is unaffected; only this one known, harmless message is
    // filtered so it doesn't fail the test run's console-output check. Any
    // other console.error still comes through and fails the test.
    const originalConsoleError = console.error.bind(console)
    sandbox.stub(console, "error").callsFake((...args) => {
      const [message] = args
      if (
        typeof message === "string" &&
        message.includes(
          'Each child in an array or iterator should have a unique "key" prop'
        ) &&
        message.includes("VictoryAxis")
      ) {
        return
      }
      originalConsoleError(...args)
    })
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

  it("renders chart", async () => {
    const { container } = renderComponent()
    const svg = await waitForChart(container)
    assert.isNotNull(svg)
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
