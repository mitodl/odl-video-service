// @flow
import { syncCollectionVideosWithEdX } from "../lib/api"

export const syncCollectionEdXEndpoint = {
  name:         "syncCollectionEdX",
  verbs:        ["post"],
  initialState: { loaded: false, processing: false, data: null },
  post:         syncCollectionVideosWithEdX
}
