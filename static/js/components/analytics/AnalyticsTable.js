// @flow
/* global SETTINGS: false */
import React from "react"
import _ from "lodash"

import type { VideoAnalyticsData } from "../../flow/videoAnalyticsTypes"

export default class AnalyticsTable extends React.Component<*, void> {
  props: {
    analyticsData: VideoAnalyticsData,
    style?: { [string]: mixed }
  }

  render() {
    const { analyticsData, style } = this.props
    return (
      <table className="mdl-data-table" style={style}>
        <thead>
          <tr>
            <th>Minute</th>
            <th>Total Viewers</th>
            {analyticsData.channels.map((channel, i) => {
              return <th key={i}>{channel}</th>
            })}
          </tr>
        </thead>
        <tbody>
          {analyticsData.times.map(minute => {
            return this.renderRowForMinute(analyticsData, minute)
          })}
        </tbody>
      </table>
    )
  }

  renderRowForMinute(
    analyticsData: VideoAnalyticsData,
    minute: string | number
  ) {
    const viewsAtTime = analyticsData.views_at_times[minute] || {}
    const totalViews = _.sum(Object.values(viewsAtTime))
    const channelViews = analyticsData.channels.map(channel => {
      return viewsAtTime[channel] || 0
    })
    const viewsValues = [totalViews, ...channelViews]
    return (
      <tr key={minute}>
        <td>{this.pad(minute, 4)}</td>
        {viewsValues.map((numViews, i) => {
          let pct = 0
          if (totalViews !== 0) {
            pct = (numViews / totalViews * 100).toFixed(1)
          }
          return (
            <td key={i}>
              {numViews} ({pct}%)
            </td>
          )
        })}
      </tr>
    )
  }

  pad(num: string | number, size: number) {
    let s = String(num)
    while (s.length < size) {
      s = `0${s}`
    }
    return s
  }
}
