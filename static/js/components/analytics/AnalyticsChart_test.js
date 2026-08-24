import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { render, waitFor } from "@testing-library/react"

import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"
import { ConditionalLabel, AnalyticsChart } from "./AnalyticsChart"
import { shouldIf } from "../../lib/test_utils"

describe("AnalyticsChartTests", () => {
  let analyticsData, padding, getColorForChannelStub, props, sandbox

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
    analyticsData = makeVideoAnalyticsData(10)
    padding = 2
    getColorForChannelStub = sandbox.stub()
    props = {
      analyticsData,
      padding,
      getColorForChannel: getColorForChannelStub
    }
  })

  afterEach(() => {
    sandbox.restore()
  })

  describe("ConditionalLabel", () => {
    // VictoryLabel's default textComponent renders a raw <text> tag. Wrapping
    // in an explicit <svg> mounts <text>/<tspan> in the SVG namespace the way
    // they're actually used in production (inside VictoryChart's own <svg>).
    const renderLabel = props => {
      return render(
        <svg>
          <ConditionalLabel {...props} />
        </svg>
      )
    }

    it("passes props to testFn", () => {
      const testProps = {
        testFn: sandbox.stub(),
        some:   "otherValue"
      }
      renderLabel(testProps)
      assert.isTrue(testProps.testFn.calledWith(testProps))
    })

    describe("when testFn returns true", () => {
      it("renders a real <text> label", () => {
        // `someProp` (the old fixture's prop) is never forwarded by Victory to
        // any DOM node -- VictoryLabel.renderElements() only clones a fixed
        // allow-list of props (including className) onto the underlying
        // <text>. Assert against props Victory actually renders instead.
        const testProps = {
          testFn:    sandbox.stub().returns(true),
          text:      "42",
          className: "conditional-label-fixture"
        }
        const { container } = renderLabel(testProps)
        const textEl = container.querySelector(
          "svg text.conditional-label-fixture"
        )
        assert.isNotNull(
          textEl,
          'expected ConditionalLabel to render a <text class="conditional-label-fixture">'
        )
        assert.equal(textEl.textContent, "42")
      })
    })

    describe("when testFn returns false", () => {
      it("returns null", () => {
        const { container } = renderLabel({
          testFn: sandbox.stub().returns(false)
        })
        assert.isNull(container.querySelector("text"))
      })
    })
  })

  describe("AnalyticsChart", () => {
    // AnalyticsChart measures its container via a 200ms setTimeout in
    // componentDidMount before it renders the Victory chart. Waiting for
    // that svg to appear makes sure the timer has already fired before
    // RTL's automatic cleanup() unmounts the tree -- otherwise the pending
    // setTimeout fires after unmount and calls setState on an unmounted
    // component, which leaks a console error into a later test's run.
    const waitForChart = container =>
      waitFor(() => {
        const svg = container.querySelector("svg")
        assert.isNotNull(svg, "expected AnalyticsChart to render an svg")
        return svg
      })

    it("renders", async () => {
      const { container } = render(<AnalyticsChart {...props} />)
      const svg = await waitForChart(container)
      assert.isNotNull(svg)
    })

    // `renderChart()`'s xMax calculation is wired into VictoryChart's
    // `domain` prop, which is not a rendered/DOM-observable value: VictoryAxis's
    // tickValues are fixed to analyticsData.times regardless of duration (so
    // rendered tick labels never change), and jsdom's getBoundingClientRect
    // defaults to an all-zero rect, which degenerates Victory's scale range to
    // zero width so tick pixel positions can't discriminate either. There is
    // no DOM representation of this fact to assert against. AnalyticsChart is
    // already dual-exported as a plain ES6 class (no production change), so
    // these three tests instantiate it directly and assert the real domain
    // computation instead of re-implementing it.
    ;[0, NaN, 6000].forEach(duration => {
      it(`${shouldIf(
        duration > 0
      )} use analytics times to determine duration`, () => {
        const instance = new AnalyticsChart({ ...props, duration })
        instance.state = { dimensions: { width: 100, height: 200 } }
        const chart = instance.renderChart()
        assert.deepEqual(chart.props.domain, {
          x: [
            0,
            duration > 0 ? duration / 60 : analyticsData.times.slice(-1)[0]
          ]
        })
      })
    })

    describe("when it unmounts", () => {
      it("removes resize handler", () => {
        const tearDownStub = sandbox.stub(
          AnalyticsChart.prototype,
          "_tearDownResizeHandler"
        )
        const { unmount } = render(<AnalyticsChart {...props} />)
        assert.isFalse(tearDownStub.called)
        unmount()
        assert.isTrue(tearDownStub.called)
      })
    })

    describe("onResize", () => {
      it("calls updateDimensions", () => {
        // Stub the prototype so componentDidMount's own deferred 200ms call
        // to _updateDimensions also resolves to this stub -- it's a no-op
        // that never touches this.rootRef or calls setState, so there is no
        // setState-after-unmount hazard here regardless of mount state when
        // that timer eventually fires.
        const updateDimensionsStub = sandbox.stub(
          AnalyticsChart.prototype,
          "_updateDimensions"
        )
        render(<AnalyticsChart {...props} />)
        assert.isFalse(updateDimensionsStub.called)
        // Dispatch the real resize event rather than calling onResize()
        // directly, to exercise the actual window listener wiring. Lodash's
        // _.throttle defaults to {leading: true}, so the first resize on a
        // fresh instance fires synchronously.
        window.dispatchEvent(new Event("resize"))
        assert.isTrue(updateDimensionsStub.called)
      })
    })
  })
})
