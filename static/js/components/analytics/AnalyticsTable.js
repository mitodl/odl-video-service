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
            {analyticsData.is_multichannel
              ? analyticsData.channels.map((channel, i) => {
                return <th key={i}>{channel}</th>
              })
              : null
            }
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
    let viewsValues = [totalViews]
    if (analyticsData.is_multichannel) {
      const channelViews = analyticsData.channels.map(channel => {
        return viewsAtTime[channel] || 0
      })

      viewsValues = [viewsValues, ...channelViews]
    }
    return (
      <tr key={minute}>
        <td className="time">{this.pad(minute, 4)}</td>
        {viewsValues.map((numViews, i) => {
          let percentEl = null
          if (analyticsData.is_multichannel) {
            let percent = 0
            if (totalViews !== 0) {
              percent = (parseFloat(numViews) / totalViews * 100).toFixed(1)
            }
            percentEl = (
              <span className="percent">{`(${percent}%)`}</span>
            )
          }
          return (
            <td className="views" key={i}>
              {numViews} {percentEl}
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
