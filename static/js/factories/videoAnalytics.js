// @flow

import type { VideoAnalyticsData } from "../flow/videoAnalyticsTypes"

export const makeVideoAnalyticsData = (n: number): VideoAnalyticsData => {
  n = n || 24
  const videoAnalyticsData = {
    times:          [...Array(n).keys()],
    channels:       [...Array(4).keys()].map(i => `channel${i + 1}`),
    views_at_times: {}
  }
  for (let tIdx = 0; tIdx < videoAnalyticsData.times.length; tIdx++) {
    const t = videoAnalyticsData.times[tIdx]
    const viewsAtTime = {}
    for (let cIdx = 0; cIdx < videoAnalyticsData.channels.length; cIdx++) {
      const channel = videoAnalyticsData.channels[cIdx]
      viewsAtTime[channel] =
        videoAnalyticsData.times.length - Math.floor((tIdx + 1) / (cIdx + 1))
    }
    videoAnalyticsData.views_at_times[t] = viewsAtTime
  }
  return videoAnalyticsData
}
