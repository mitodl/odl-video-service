import React from "react"
import _ from "lodash"

import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"
import AnalyticsChart from "./AnalyticsChart"
import AnalyticsInfoTable from "./AnalyticsInfoTable"
import ProgressSlider from "./ProgressSlider"

const COLORS = [
  { name: "lightBlue", hex: "#61befd" },
  { name: "darkBlue", hex: "#3976c7" },
  { name: "green", hex: "#6ac360" },
  { name: "yellow", hex: "#fce63c" }
]

const CHART_PADDING = {
  top:    10,
  bottom: 60,
  left:   75,
  right:  20
}

export class AnalyticsPane extends React.Component {
  render() {
    const {
      currentTime,
      duration,
      analyticsData,
      setVideoTime,
      ...passThroughProps
    } = this.props
    const analyticsData_ =
      analyticsData || makeVideoAnalyticsData(Math.floor(duration / 60) + 1)
    const colorsForChannels = {}
    for (let i = 0; i < analyticsData_.channels.length; i++) {
      colorsForChannels[analyticsData_.channels[i]] = COLORS[i]
    }
    const getColorForChannel = channel => colorsForChannels[channel].hex
    let className = "analytics-overlay"
    if (this.props.className) {
      className += ` ${this.props.className}`
    }
    return (
      <div className={className} {..._.omit(passThroughProps, ["video"])}>
        <div
          style={{
            width:         "100%",
            height:        "80%",
            display:       "flex",
            flexDirection: "column"
          }}
        >
          <AnalyticsInfoTable
            analyticsData={analyticsData_}
            getColorForChannel={getColorForChannel}
            currentTime={currentTime}
            style={{
              width: "100%",
              flex:  "0 0 4em"
            }}
          />
          <hr style={{ width: "100%" }} />
          <div
            className="chart-container"
            style={{
              flex:     "1 1 auto",
              width:    "100%",
              height:   "100%",
              position: "relative"
            }}
          >
            <AnalyticsChart
              analyticsData={analyticsData_}
              getColorForChannel={getColorForChannel}
              currentTime={currentTime}
              duration={duration}
              padding={CHART_PADDING}
              style={{
                width:  "100%",
                height: "100%"
              }}
            />
            <ProgressSlider
              value={currentTime / duration}
              style={{
                fontSize: "10px",
                position: "absolute",
                left:     `${CHART_PADDING.left}px`,
                right:    `${CHART_PADDING.right}px`,
                bottom:   `${CHART_PADDING.bottom - 5}px` // 5 is alignment fudge
              }}
              onChange={nextValue => {
                setVideoTime(nextValue * duration)
              }}
            />
          </div>
        </div>
      </div>
    )
  }
}

export default AnalyticsPane
