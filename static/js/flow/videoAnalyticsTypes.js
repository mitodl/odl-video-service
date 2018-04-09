// @flow

export type VideoAnalyticsData = {
  channels: Array<string|number>,
  times: Array<string|number>,
  views_at_times: {
    [string | number]: {
      [string | number]: number
    }
  }
}
