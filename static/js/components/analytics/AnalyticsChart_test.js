import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { render, waitFor } from "@testing-library/react"

import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"
import { ConditionalLabel, AnalyticsChart } from "./AnalyticsChart"
import { shouldIf } from "../../lib/test_utils"

import suppressVictoryKeyWarning from "../../testUtils/suppressVictoryKeyWarning"

describe("AnalyticsChartTests", () => {
  let analyticsData, padding, getColorForChannelStub, props, sandbox

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    // AnalyticsChart mounts a real Victory chart whose VictoryAxis emits a
    // spurious React "unique key prop" warning; see the helper for why it
    // is filtered here and nowhere else. This used to be an inline copy of
    // the helper's logic; the duplicate went stale when React 16 reworded
    // the message, so the two call sites now share one implementation.
    suppressVictoryKeyWarning(sandbox)
    analyticsData = makeVideoAnalyticsData(10)
    // Must be the {top, bottom, left, right} object AnalyticsPane passes as
    // CHART_PADDING. A bare number is a valid Victory `padding`, but
    // AnalyticsChart also reads padding.left/right/top/bottom directly --
    // for the clip-path rect's width/height and the dependent axis's
    // offsetX -- so a number made all four NaN. React 15 rendered NaN
    // attributes silently; React 16 reports each one.
    padding = { top: 10, bottom: 60, left: 75, right: 20 }
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
    // componentDidMount before it renders the Victory chart, so the svg
    // is not in the DOM synchronously after render. Waiting for it is how
    // these tests observe a drawn chart.
    //
    // This previously also guarded against the timer firing after RTL's
    // cleanup() and calling setState on an unmounted component. R1 fixed
    // that at the cause -- componentWillUnmount now clears the timer --
    // so this helper is only about waiting for render.
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
        const tearDownStub = sandbox.spy(
          AnalyticsChart.prototype,
          "_tearDownResizeHandler"
        )
        const { unmount } = render(<AnalyticsChart {...props} />)
        assert.isFalse(tearDownStub.called)
        unmount()
        assert.isTrue(tearDownStub.called)
      })

      it("clears the pending dimensions timer", () => {
        const updateDimensionsStub = sandbox.stub(
          AnalyticsChart.prototype,
          "_updateDimensions"
        )
        const clock = sandbox.useFakeTimers()

        const { unmount } = render(<AnalyticsChart {...props} />)
        unmount()
        clock.tick(200)

        // Without clearTimeout this fires after unmount and calls
        // setState on a dead component.
        assert.isFalse(updateDimensionsStub.called)
      })

      it("cancels pending throttled resize work", () => {
        // _resizeHandler is _.throttle'd, so removeEventListener alone
        // leaves a queued trailing invocation that still calls setState
        // after unmount. Driven through a real instance because RTL gives
        // no access to it and the throttle queue is instance state --
        // the same reason the `domain` tests above instantiate directly.
        const updateDimensionsStub = sandbox.stub(
          AnalyticsChart.prototype,
          "_updateDimensions"
        )
        const clock = sandbox.useFakeTimers()

        const instance = new AnalyticsChart(props)
        instance._setupResizeHandler()

        // Two calls inside the 100ms window: the first invokes on the
        // leading edge, the second queues a trailing invocation.
        instance._resizeHandler()
        instance._resizeHandler()
        assert.equal(updateDimensionsStub.callCount, 1)

        instance.componentWillUnmount()
        clock.tick(100)

        assert.equal(updateDimensionsStub.callCount, 1)
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
