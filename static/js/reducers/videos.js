// @flow
import { GET, PATCH, INITIAL_STATE } from "redux-hammock/constants"

import * as api from "../lib/api"

import type { Video, VideoUpdatePayload } from "../flow/videoTypes"

export const videosEndpoint = {
  name:              "videos",
  verbs:             [GET, PATCH, "DELETE"],
  initialState:      { ...INITIAL_STATE, data: new Map() },
  getFunc:           (videoKey: string): Promise<Video> => api.getVideo(videoKey),
  getSuccessHandler: (payload: Video, data: Map<string, Video>) => {
    const update: Map<string, Video> = new Map(data)
    update.set(payload.key, payload)
    return update
  },
  patchFunc: (videoKey: string, payload: VideoUpdatePayload) =>
    api.updateVideo(videoKey, payload),
  patchSuccessHandler: (payload: Video, data: Map<string, Video>) => {
    const update: Map<string, Video> = new Map(data)
    update.set(payload.key, payload)
    return update
  },
  deleteFunc: (videoKey: string): Promise<Video> => api.deleteVideo(videoKey)
}
