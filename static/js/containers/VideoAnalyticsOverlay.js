import React from "react"

import AnalyticsPane from "../components/analytics/AnalyticsPane"
import LoadingIndicator from "../components/material/LoadingIndicator"

import withVideoAnalytics from "./withVideoAnalytics"
import { actions } from "../actions"


export class VideoAnalyticsOverlay extends React.Component { 
  render () {
    const { video, videoAnalytics, ...passThroughProps } = this.props
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
      <AnalyticsPane
        analyticsData={analyticsData}
        video={video}
        {...passThroughProps}
      />
    )
  }
}

export const ConnectedVideoAnalyticsOverlay = withVideoAnalytics(VideoAnalyticsOverlay)

export default ConnectedVideoAnalyticsOverlay
