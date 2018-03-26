// @flow
/* global SETTINGS: false */
import React from "react"
import _ from "lodash"

import { TabBar, Tab } from "rmwc/Tabs"

import AnalyticsChart from "./AnalyticsChart"
import AnalyticsTable from "./AnalyticsTable"
import type { Video } from "../../flow/videoTypes"
import type { VideoAnalyticsData } from "../../flow/videoAnalyticsTypes"

import { makeVideoUrl } from "../../lib/urls"

const CSS_NS = "analytics-pane"

type Props = {
  analyticsData: VideoAnalyticsData | null,
  video: Video,
  style?: { [string]: mixed }
}

class AnalyticsPane extends React.Component<*, *> {
  _tabDefs: Array<{ title: string, renderFn: Function }>

  state: {
    activeTabIndex: number
  }

  constructor(props: Props) {
    super(props)
    this._tabDefs = [
      {
        title:    "Graph",
        renderFn: this.renderChart.bind(this)
      },
      {
        title:    "Table",
        renderFn: this.renderTable.bind(this)
      }
    ]
    this.state = {
      activeTabIndex: 0
    }
  }

  render() {
    if (!this.props.video) {
      return null
    }
    return (
      <section style={this.props.style}>
        {this.renderHeader()}
        {this.renderBody()}
      </section>
    )
  }

  renderHeader() {
    const { video } = this.props
    const videoUrl = `${window.location.origin}${makeVideoUrl(video.key)}`
    return (
      <header className={`${CSS_NS}-header`}>
        <div
          style={{
            display:        "flex",
            flexDirection:  "row",
            justifyContent: "space-between"
          }}
        >
          <h2
            className={`${CSS_NS}-video-title`}
            style={{
              margin:     0,
              fontWeight: "500",
              fontSize:   "large"
            }}
          >{`Views per minute for video "${video.title}"`}</h2>
        </div>
        <a
          className={`${CSS_NS}-video-link`}
          style={{ fontSize: "small" }}
          href={videoUrl}
        >
          {videoUrl}
        </a>
      </header>
    )
  }

  renderBody() {
    const { analyticsData } = this.props
    const bodyContent = this.analyticsDataIsEmpty(analyticsData)
      ? this.renderEmptyDataMessage()
      : this.renderTabs()
    return (
      <section className={`${CSS_NS}-body`} style={{ width: "100%" }}>
        {bodyContent}
      </section>
    )
  }

  analyticsDataIsEmpty(analyticsData: any): boolean {
    return !!analyticsData && _.isEmpty(analyticsData.times)
  }

  renderTabs() {
    const { analyticsData } = this.props
    const formattedAnalyticsData = this.formatAnalyticsData(analyticsData)
    return (
      <section>
        <TabBar
          activeTabIndex={this.state.activeTabIndex}
          onChange={evt => this.setState({ activeTabIndex: evt.target.value })}
          style={{
            marginLeft:   0,
            borderBottom: "thin solid #333",
            width:        "100%"
          }}
        >
          {this._tabDefs.map(tabDef => {
            return <Tab key={tabDef.title}>{tabDef.title}</Tab>
          })}
        </TabBar>
        <section>
          {this._tabDefs[this.state.activeTabIndex].renderFn(
            formattedAnalyticsData
          )}
        </section>
      </section>
    )
  }

  formatAnalyticsData(analyticsData: VideoAnalyticsData): VideoAnalyticsData {
    return {
      channels:       analyticsData.channels,
      times:          this.interpolateTimes(analyticsData.times),
      views_at_times: analyticsData.views_at_times
    }
  }

  interpolateTimes(times: Array<string | number>): Array<string | number> {
    const maxTime = _.maxBy(times, time => parseInt(time, 10))
    const interpolatedTimes = [...Array(maxTime + 1).keys()]
    return interpolatedTimes
  }

  renderEmptyDataMessage() {
    return (
      <section
        className={`${CSS_NS}-empty-data-message`}
        style={{
          textAlign:  "center",
          marginTop:  "1em",
          paddingTop: "1em",
          borderTop:  "thin solid grey"
        }}
      >
        <div>No analytics data for this video at this time.</div>
      </section>
    )
  }

  renderChart(analyticsData: VideoAnalyticsData) {
    return (
      <AnalyticsChart analyticsData={analyticsData} style={{ width: "100%" }} />
    )
  }

  renderTable(analyticsData: VideoAnalyticsData) {
    return (
      <AnalyticsTable analyticsData={analyticsData} style={{ width: "100%" }} />
    )
  }
}

export default AnalyticsPane
