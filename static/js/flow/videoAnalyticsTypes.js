// @flow

export type VideoAnalyticsData = {
  channels: Array<string>,
  is_multichannel: boolean,
  times: Array<string|number>,
  views_at_times: {
    [string | number]: {
      [string | number]: number
    }
  }
}
