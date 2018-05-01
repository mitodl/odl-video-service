import React from "react"
import _ from "lodash"
import { VictoryChart, VictoryBar, VictoryAxis, VictoryStack } from "victory"
import { VictoryLabel, ClipPath } from "victory"

// Helper to selectively show labels in Victory charts
export class ConditionalLabel extends React.Component {
  render() {
    const { testFn, ...passThroughProps } = this.props
    if (testFn(this.props)) {
      return <VictoryLabel {...passThroughProps} />
    }
    return null
  }
}

export class AnalyticsChart extends React.Component {
  props: {
    analyticsData: VideoAnalyticsData,
    getColorForChannel: Function,
    currentTime: number,
    style?: { [string]: mixed }
  }

  constructor(props) {
    super(props)
    this._namespace = Math.floor(1e6 * Math.random()) // used for ids in svg
    this.state = {
      dimensions: null
    }
  }
  componentDidMount() {
    this._setupResizeHandler()
    setTimeout(() => this._updateDimensions(), 200)
  }

  _setupResizeHandler() {
    this._resizeHandler = _.throttle(this.onResize.bind(this), 100)
    window.addEventListener("resize", this._resizeHandler)
  }

  onResize() {
    this._updateDimensions()
  }

  _tearDownResizeHandler() {
    window.removeEventListener("resize", this._resizeHandler)
  }

  _updateDimensions() {
    if (!this.rootRef) {
      return
    }
    const { width, height } = this.rootRef.getBoundingClientRect()
    this.setState({ dimensions: { width, height } })
  }

  componentWillUnmount() {
    this._tearDownResizeHandler()
  }

  render() {
    const { dimensions } = this.state
    const passThroughProps = _.omit(this.props, [
      "analyticsData",
      "currentTime",
      "duration",
      "getColorForChannel",
      "padding",
      "setVideoTime"
    ])
    return (
      <div
        ref={ref => {
          this.rootRef = ref
        }}
        {...passThroughProps}
      >
        {dimensions ? this.renderChart() : null}
      </div>
    )
  }

  renderChart() {
    const { dimensions } = this.state
    const { analyticsData, duration, getColorForChannel, padding } = this.props
    if (!dimensions || !padding) {
      return null
    }
    const viewsAtTimesByChannel = this._generateViewsAtTimesByChannel(
      analyticsData)
    const baseLabelStyle = {
      fill:       "#666",
      fontFamily: "'Roboto', 'sans-serif'",
      fontSize:   10
    }
    const chartBodyClipPathId = `${this._namespace}-chart-body-clipPath`
    const chartBodyBounds = this._getRelativeChartBodyBounds()
    return (
      <VictoryChart
        {...dimensions}
        domain={{ x: [0, duration / 60 || 1] }}
        domainPadding={{ x: [0, 0], y: [0, 0] }}
        padding={padding}
      >
        <VictoryAxis
          tickValues={analyticsData.times}
          tickFormat={(t) => {
            return `${t}m`
          }}
          style={{
            axis: {
              stroke: "black"
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
          crossAxis={true}
          tickLabelComponent={
            <ConditionalLabel
              testFn={props => {
                return props.datum % 5 === 0
              }}
            />
          }
        />
        <VictoryAxis
          dependentAxis
          label="views"
          offsetX={padding.left - 2}
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

        <ClipPath clipId={chartBodyClipPathId}>
          <rect {...chartBodyBounds} />
        </ClipPath>

        <VictoryStack
          groupComponent={
            <g
              clipPath={`url(#${chartBodyClipPathId})`}
              className="chart-body"
            />
          }
        >
          {analyticsData.channels.map((channel, i) => {
            return (
              <VictoryBar
                key={i}
                data={viewsAtTimesByChannel[channel]}
                alignment="start"
                barRatio={1.0}
                x="time"
                y="views"
                style={{
                  data: {
                    fill: getColorForChannel(channel)
                  }
                }}
              />
            )
          })}
        </VictoryStack>
      </VictoryChart>
    )
  }

  _getRelativeChartBodyBounds() {
    const padding = this.props.padding
    if (!padding) {
      return null
    }
    const { dimensions } = this.state
    if (!dimensions || !padding) {
      return null
    }
    return {
      x:      padding.left,
      y:      padding.top,
      width:  dimensions.width - (padding.left + padding.right),
      height: dimensions.height - (padding.top + padding.bottom)
    }
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
}

export default AnalyticsChart
