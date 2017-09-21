// @flow
import { POST, INITIAL_STATE } from "redux-hammock/constants";

import * as api from "../lib/api";
import type { VideoSubtitle } from "../flow/videoTypes";

export const videoSubtitlesEndpoint = {
  name: "videoSubtitles",
  verbs: [POST, "DELETE"],
  initialState: { ...INITIAL_STATE, data: new Map() },
  postFunc: (payload: FormData): Promise<VideoSubtitle> => (
    api.createSubtitle(payload)
  ),
  deleteFunc: (videoSubtitleKey: number) => (
    api.deleteSubtitle(videoSubtitleKey)
  )
};
