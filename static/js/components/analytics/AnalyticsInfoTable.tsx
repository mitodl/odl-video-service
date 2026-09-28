import React from "react"
import _ from "lodash"

import type { VideoAnalyticsData } from "../../types/videoAnalyticsTypes"

type Props = {
  analyticsData: VideoAnalyticsData
  getColorForChannel: (channel: string) => string
  currentTime: number
  style?: React.CSSProperties
}

type ColumnSpec = {
  key: string
  className: string
  labelEl: React.ReactNode
  valueEl: React.ReactNode
}

export default class AnalyticsInfoTable extends React.Component<Props> {
  render() {
    const { analyticsData, currentTime, style } = this.props
    const columnSpecs = this.generateColumnSpecs({
      analyticsData,
      time: currentTime
    })
    const columnStyles: { [key: string]: React.CSSProperties } = {
      th: { fontWeight: "normal", fontSize: "90%" },
      td: { fontWeight: "bold", textAlign: "center" }
    }
    return (
      <table style={style}>
        <thead>
          <tr>
            {columnSpecs.map(columnSpec => {
              return (
                <th
                  key={columnSpec.key}
                  className={columnSpec.className}
                  style={columnStyles.th}
                >
                  {columnSpec.labelEl}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          <tr>
            {columnSpecs.map(columnSpec => {
              return (
                <td
                  key={columnSpec.key}
                  className={columnSpec.className}
                  style={columnStyles.td}
                >
                  {columnSpec.valueEl}
                </td>
              )
            })}
          </tr>
        </tbody>
      </table>
    )
  }

  generateColumnSpecs(opts: {
    analyticsData: VideoAnalyticsData
    time: number
  }): Array<ColumnSpec> {
    const { analyticsData, time } = opts
    const minute = Math.floor(time / 60)
    const viewsAtTime = analyticsData.views_at_times[minute] || {}
    const totalViews = _.sum(Object.values(viewsAtTime))
    let columnSpecs: Array<ColumnSpec> = [
      {
        key:       "time",
        className: "time",
        labelEl:   "time",
        valueEl:   this.secondsToTimeStr(time)
      }
    ]
    if (analyticsData.is_multichannel) {
      columnSpecs = [
        ...columnSpecs,
        {
          key:       "total-views",
          className: "total-views",
          labelEl:   <span>total views</span>,
          valueEl:   <span>{totalViews}</span>
        },
        ...analyticsData.channels.map(channel => {
          // `parseFloat` stringifies its argument before parsing, so wrapping
          // in `String` is what the call already did implicitly; it only makes
          // the coercion visible to the typechecker.
          const numViews = parseFloat(String(viewsAtTime[channel] || 0))
          const percent = totalViews === 0 ? 0 : (numViews / totalViews) * 100
          return {
            key:       channel,
            className: `channel ${channel}`,
            labelEl:   this.renderLabelForChannel(channel),
            valueEl:   (
              <span>
                {numViews} ({percent.toFixed(1)}%)
              </span>
            )
          }
        })
      ]
    } else {
      columnSpecs = [
        ...columnSpecs,
        {
          key:       "views",
          className: "total-views",
          labelEl:   <span>views</span>,
          valueEl:   <span>{totalViews}</span>
        }
      ]
    }
    return columnSpecs
  }

  renderLabelForChannel(channel: string) {
    const style: React.CSSProperties = {
      marginRight:     ".5em",
      width:           10,
      height:          10,
      backgroundColor: this.props.getColorForChannel(channel),
      display:         "inline-block"
    }
    return (
      <span>
        <span style={style} />
        {channel}
      </span>
    )
  }

  secondsToTimeStr(seconds: number) {
    const minutes = Math.floor(seconds / 60)
    const remainder = Math.floor(seconds - 60 * minutes)
    return `${this.pad(minutes, 2)}:${this.pad(remainder, 2)}`
  }

  pad(num: string | number, size: number) {
    let s = String(num)
    while (s.length < size) {
      s = `0${s}`
    }
    return s
  }
}
