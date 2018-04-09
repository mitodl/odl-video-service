// @flow
import { GET, INITIAL_STATE } from "redux-hammock/constants"

import * as api from "../lib/api"
import type { VideoAnalyticsData } from "../flow/videoAnalyticsTypes"

type Payload = {
  key: string | number,
  data: VideoAnalyticsData
}

export const videoAnalyticsEndpoint = {
  name:         "videoAnalytics",
  verbs:        [GET],
  initialState: { ...INITIAL_STATE, data: new Map() },
  getFunc:      (videoKey: string): Promise<Payload> => {
    return api.getVideoAnalytics(videoKey)
  },
  getSuccessHandler: (
    payload: Payload,
    data: Map<string | number, VideoAnalyticsData>
  ) => {
    const update: Map<string | number, VideoAnalyticsData> = new Map(data)
    update.set(payload.key, payload.data)
    return update
  }
}
