// @flow
/* global SETTINGS: false */
import React from "react"
import { assert } from "chai"
import { shallow } from "enzyme"
import sinon from "sinon"

import { makeVideo } from "../factories/video"
import { makeVideoAnalyticsData } from "../factories/videoAnalytics"

import { VideoAnalyticsOverlay } from "./VideoAnalyticsOverlay"
import { actions } from "../actions"


describe("VideoAnalyticsOverlay", () => {
  let props, sandbox

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
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

  const renderComponent = ((extraProps = {}) => {
    return shallow(
      <VideoAnalyticsOverlay {...{...props, ...extraProps}} />
    )
  })

  it("renders nothing if no video or no videoAnalytics", () => {
    const wrapper = renderComponent({
      video:          undefined,
      videoAnalytics: undefined
    })
    assert.equal(wrapper.type(), null)
  })

  it("renders nothing if no videoAnalytics data", () => {
    const wrapper = renderComponent({
      videoAnalytics: {
        ...props.videoAnalytics,
        data: new Map(),
      }
    })
    assert.equal(wrapper.type(), null)
  })

  it("renders loading indicator if loading", () => {
    const wrapper = renderComponent({
      videoAnalytics: {
        ...props.videoAnalytics,
        processing: true
      }
    })
    assert.equal(wrapper.find('LoadingIndicator').length, 1)
  })

  describe("when there is error", () => {
    let wrapper, dispatchSpy

    beforeEach(() => {
      dispatchSpy = sandbox.spy()
      wrapper = renderComponent({
        dispatch:       dispatchSpy,
        videoAnalytics: {
          ...props.videoAnalytics,
          error: "some error"
        }
      })
    })

    it("renders error indicator if error", () => {
      assert.equal(wrapper.find('.error-indicator').length, 1)
    })

    it("dispatches clear action when 'try again' button is clicked", () => {
      const tryAgainButton = wrapper.find('.error-indicator').find(".try-again")
      sinon.assert.notCalled(dispatchSpy)
      tryAgainButton.simulate('click')
      sinon.assert.calledWith(dispatchSpy, actions.videoAnalytics.clear())
    })
  })

  it("renders AnalyticsPane w/ expected props", () => {
    const extraProps = {a: '1', b: '2'}
    const wrapper = renderComponent(extraProps)
    const AnalyticsPane = wrapper.find('AnalyticsPane')
    assert.isTrue(AnalyticsPane.exists())
    assert.deepEqual(
      AnalyticsPane.props(),
      {
        analyticsData: props.videoAnalytics.data.get(props.video.key),
        video:         props.video,
        ...extraProps
      }
    )
  })
})
