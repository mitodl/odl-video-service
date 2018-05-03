import React from "react"
import _ from "lodash"

import AnalyticsPane from "../components/analytics/AnalyticsPane"
import LoadingIndicator from "../components/material/LoadingIndicator"

import withVideoAnalytics from "./withVideoAnalytics"
import { actions } from "../actions"


export class VideoAnalyticsOverlay extends React.Component { 
  renderCloseButton() {
    return (
      <span
        className="close-button"
        style={{position: 'absolute', right: 0, top: 0, zIndex: 100}}
        onClick={this.props.onClose}>
        <i className="material-icons active" style={{fontSize: '36px'}}>highlight_off</i>
      </span>
    )
  }

  render () {
    const { video, videoAnalytics, ...extraProps } = this.props
    const passThroughProps = _.omit(extraProps, ['onClose', 'showCloseButton'])
    if (!video || !videoAnalytics) {
      return null
    }
    if (videoAnalytics.processing) {
      return (<LoadingIndicator />)
    }
    if (!videoAnalytics.data || !videoAnalytics.data.get(video.key)) {
      return null
    }
    if (videoAnalytics.error) {
      return (
        <div className="error-indicator">
          Could not load analytics for video.
          <button className="try-again" onClick={() => {
            this.props.dispatch(actions.videoAnalytics.clear())
          }}>try again</button>
        </div>
      )
    }
    const analyticsData = videoAnalytics.data.get(video.key)
    return (
      <div style={{width: '100%', height: '100%', position: 'relative'}}>
        {this.props.showCloseButton ? this.renderCloseButton() : null}
        <AnalyticsPane
          analyticsData={analyticsData}
          video={video}
          {...passThroughProps}
        />
      </div>
    )
  }
}

export const ConnectedVideoAnalyticsOverlay = withVideoAnalytics(VideoAnalyticsOverlay)

export default ConnectedVideoAnalyticsOverlay
