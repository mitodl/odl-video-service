// @flow
/* global SETTINGS: false */
import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"

import { makeVideo } from "../factories/video"
import { makeVideoAnalyticsData } from "../factories/videoAnalytics"

import { VideoAnalyticsOverlay } from "./VideoAnalyticsOverlay"
import { actions } from "../actions"
import suppressVictoryKeyWarning from "../testUtils/suppressVictoryKeyWarning"

describe("VideoAnalyticsOverlay", () => {
  let props, sandbox

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    // AnalyticsPane (rendered whenever there's data, no error, and it's not
    // loading) mounts a real Victory chart via AnalyticsChart, whose
    // VictoryAxis emits a spurious React "unique key prop" warning; see the
    // helper for why it is filtered here and nowhere else.
    suppressVictoryKeyWarning(sandbox)
    const video = makeVideo()
    props = {
      video,
      videoAnalytics: {
        data:       new Map([[video.key, makeVideoAnalyticsData()]]),
        loaded:     true,
        processing: false
      }
    }
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (extraProps = {}) => {
    return render(<VideoAnalyticsOverlay {...{ ...props, ...extraProps }} />)
  }

  // AnalyticsChart measures its container via a 200ms setTimeout in
  // componentDidMount before it renders the Victory chart into
  // .chart-container. Waiting for that svg to appear -- in every test that
  // mounts AnalyticsPane, not just ones asserting on the chart -- makes
  // sure the timer has already fired before RTL's automatic cleanup()
  // unmounts the tree. Otherwise the pending setTimeout fires after
  // unmount and calls setState on an unmounted component.
  const waitForChart = container =>
    waitFor(() => {
      const svg = container.querySelector(".chart-container svg")
      assert.isNotNull(svg, "expected AnalyticsChart to render an svg")
      return svg
    })

  // React 15's ReactDOM leaves a placeholder Comment node in the container
  // when a component renders null, so `firstElementChild` (which ignores
  // comment nodes) is the honest way to assert "renders nothing" here --
  // `firstChild` would find the comment and report non-null.
  it("renders nothing if no video or no videoAnalytics", () => {
    const { container } = renderComponent({
      video:          undefined,
      videoAnalytics: undefined
    })
    assert.isNull(container.firstElementChild)
  })

  it("renders nothing if no videoAnalytics data", () => {
    const { container } = renderComponent({
      videoAnalytics: {
        ...props.videoAnalytics,
        data: new Map()
      }
    })
    assert.isNull(container.firstElementChild)
  })

  it("renders loading indicator if loading", () => {
    renderComponent({
      videoAnalytics: {
        ...props.videoAnalytics,
        processing: true
      }
    })
    assert.isNotNull(screen.getByText("Loading..."))
  })

  describe("when there is error", () => {
    let dispatchSpy

    beforeEach(() => {
      dispatchSpy = sandbox.spy()
      renderComponent({
        dispatch:       dispatchSpy,
        videoAnalytics: {
          ...props.videoAnalytics,
          error: "some error"
        }
      })
    })

    it("renders error indicator if error", () => {
      assert.isNotNull(screen.getByText("Could not load analytics for video."))
    })

    it("dispatches clear action when 'try again' button is clicked", () => {
      const tryAgainButton = screen.getByRole("button", { name: "try again" })
      sinon.assert.notCalled(dispatchSpy)
      fireEvent.click(tryAgainButton)
      sinon.assert.calledWith(dispatchSpy, actions.videoAnalytics.clear())
    })
  })

  it("renders AnalyticsPane with the current video's own analytics data, not another video's", async () => {
    // The Map holds analytics data for more than one video, keyed by
    // video.key. This asserts that VideoAnalyticsOverlay selects out
    // props.video's own entry (data.get(video.key)) rather than some other
    // entry, by rendering distinguishable data for each and checking which
    // one AnalyticsPane's table actually displays. It also confirms
    // arbitrary extra props still pass through to AnalyticsPane.
    const otherVideo = makeVideo()
    const { container } = renderComponent({
      videoAnalytics: {
        ...props.videoAnalytics,
        data: new Map([
          [props.video.key, makeVideoAnalyticsData(2)],
          [otherVideo.key, makeVideoAnalyticsData(3, false)]
        ])
      },
      currentTime:  0,
      duration:     1,
      setVideoTime: sandbox.spy(),
      id:           "video-analytics-overlay-extra-prop"
    })
    await waitForChart(container)

    const totalViewsEl = container.querySelector("td.total-views")
    assert.isNotNull(
      totalViewsEl,
      "expected a td.total-views element to render"
    )
    assert.equal(totalViewsEl.textContent, "7")
    assert.isNotNull(
      container.querySelector("#video-analytics-overlay-extra-prop"),
      "expected extra props to pass through to AnalyticsPane"
    )
  })

  describe("close button", () => {
    describe("when showCloseButton is true", () => {
      let container, onCloseSpy

      beforeEach(async () => {
        onCloseSpy = sandbox.spy()
        const rendered = renderComponent({
          showCloseButton: true,
          onClose:         onCloseSpy
        })
        container = rendered.container
        await waitForChart(container)
      })

      it("renders button", () => {
        assert.isNotNull(container.querySelector(".close-button"))
      })

      it("triggers props.onClose when button is clicked", () => {
        sinon.assert.notCalled(onCloseSpy)
        fireEvent.click(container.querySelector(".close-button"))
        sinon.assert.called(onCloseSpy)
      })
    })

    describe("when showCloseButton is not true", () => {
      let container

      beforeEach(async () => {
        const rendered = renderComponent({ showCloseButton: false })
        container = rendered.container
        await waitForChart(container)
      })

      it("does not render button", () => {
        assert.isNull(container.querySelector(".close-button"))
      })
    })
  })
})
