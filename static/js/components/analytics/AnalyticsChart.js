import React from "react"
import { VictoryChart, VictoryBar, VictoryAxis, VictoryStack } from "victory"
import { VictoryLabel, VictoryTooltip } from "victory"

// Helper to selectively show labels in Victory charts
class ConditionalLabel extends React.Component {
  render() {
    if (this.props.testFn(this.props)) {
      return <VictoryLabel {...this.props} />
    }
    return null
  }
}

class AnalyticsChart extends React.Component {
  render() {
    const { analyticsData } = this.props
    const viewsAtTimesByChannel = this._generateViewsAtTimesByChannel(
      analyticsData
    )
    const colors = [
      { name: "lightBlue", hex: "#61befd" },
      { name: "darkBlue", hex: "#3976c7" },
      { name: "green", hex: "#6ac360" },
      { name: "yellow", hex: "#fce63c" }
    ]
    const baseLabelStyle = {
      fill:       "#666",
      fontFamily: "'Roboto', 'sans-serif'",
      fontSize:   10
    }
    return (
      <div style={{ width: "100%" }}>
        <VictoryChart
          height={250}
          domain={{
            x: [-0.5, analyticsData.times[analyticsData.times.length - 1]]
          }}
          domainPadding={{ x: [0, 7], y: [0, 0] }}
          padding={{ top: 55, bottom: 50, left: 60, right: 60 }}
        >
          <VictoryAxis
            label="time"
            tickValues={analyticsData.times}
            tickFormat={t => {
              return `${t}m`
            }}
            style={{
              axis: {
                stroke: "black"
              },
              axisLabel: {
                ...baseLabelStyle
              },
              ticks: {
                stroke: "black",
                size:   2
              },
              tickLabels: {
                ...baseLabelStyle,
                textAnchor: "middle",
                padding:    2
              }
            }}
            tickLabelComponent={
              <ConditionalLabel
                testFn={props => {
                  if (props.datum % 10 === 0) {
                    return true
                  }
                  if (props.index + 1 === analyticsData.times.length) {
                    return true
                  }
                  return false
                }}
              />
            }
            crossAxis={true}
          />
          <VictoryAxis
            dependentAxis
            label="# views"
            offsetX={50}
            style={{
              axis: {
                padding: 100
              },
              axisLabel: {
                ...baseLabelStyle
              },
              grid: {
                stroke: "#eee"
              },
              ticks: {
                stroke: "black",
                size:   2
              },
              tickLabels: {
                ...baseLabelStyle,
                padding: 4
              }
            }}
            tickCount={10}
            tickLabelComponent={
              <ConditionalLabel
                testFn={props => {
                  return props.index % 2 !== 0
                }}
              />
            }
          />
          <VictoryStack>
            {analyticsData.channels.map((channel, i) => {
              return (
                <VictoryBar
                  key={i}
                  barRatio={1.0}
                  data={viewsAtTimesByChannel[channel]}
                  alignment="middle"
                  x="time"
                  y="views"
                  style={{
                    data: {
                      fill: colors[i].hex
                    }
                  }}
                  labels={d => `${channel}, ${d.x}m: ${d.y}`}
                  labelComponent={<VictoryTooltip />}
                />
              )
            })}
          </VictoryStack>
        </VictoryChart>
        {this.renderLegend({ analyticsData, colors })}
      </div>
    )
  }

  _generateViewsAtTimesByChannel(analyticsData) {
    const viewsAtTimesByChannel = {}
    for (const channel of analyticsData.channels) {
      viewsAtTimesByChannel[channel] = []
    }
    for (const time of analyticsData.times) {
      const viewsAtTime = analyticsData.views_at_times[time] || {}
      for (const channel of analyticsData.channels) {
        viewsAtTimesByChannel[channel].push({
          time:  time,
          views: viewsAtTime[channel] || 0
        })
      }
    }
    return viewsAtTimesByChannel
  }

  renderLegend(opts) {
    const { analyticsData, colors } = opts
    return (
      <div style={{ textAlign: "center", marginTop: "-1em" }}>
        <ul
          style={{
            display:   "inline-block",
            border:    "thin solid #ddd",
            listStyle: "none",
            margin:    0
          }}
        >
          {analyticsData.channels.map((channel, i) => {
            const style = {
              marginLeft:      ".5em",
              width:           10,
              height:          10,
              backgroundColor: colors[i].hex,
              display:         "inline-block"
            }
            return (
              <li key={i} style={{ display: "inline-block", padding: 10 }}>
                {channel}
                <span style={style} />
              </li>
            )
          })}
        </ul>
      </div>
    )
  }
}

export default AnalyticsChart
