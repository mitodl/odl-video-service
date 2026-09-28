export type VideoAnalyticsData = {
  channels: Array<string>
  is_multichannel: boolean
  times: Array<string | number>
  // Flow allowed `[string | number]` as a key type. TypeScript index
  // signatures take one key type, and JavaScript coerces numeric keys to
  // strings anyway, so `string` covers both.
  views_at_times: {
    [key: string]: {
      [key: string]: number
    }
  }
}
