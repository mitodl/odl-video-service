// @flow
import {
  collectionsListEndpoint,
  collectionsEndpoint,
  uploadVideoEndpoint
} from "../reducers/collections"
import { videosEndpoint } from "../reducers/videos"
import { videoSubtitlesEndpoint } from "../reducers/videoSubtitles"
import { videoAnalyticsEndpoint } from "../reducers/videoAnalytics"
import { syncCollectionEdXEndpoint } from "../reducers/syncCollectionEdX"
import { usersListEndpoint } from "../reducers/users"


export const endpoints = [
  collectionsListEndpoint,
  collectionsEndpoint,
  uploadVideoEndpoint,
  videosEndpoint,
  videoSubtitlesEndpoint,
  videoAnalyticsEndpoint,
  syncCollectionEdXEndpoint,
  usersListEndpoint
]
