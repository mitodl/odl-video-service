// @flow
import {
  collectionsListEndpoint,
  collectionsEndpoint,
  uploadVideoEndpoint
} from "../reducers/collections"
import { videosEndpoint } from "../reducers/videos"
import { videoSubtitlesEndpoint } from "../reducers/videoSubtitles"
import { syncCollectionEdXEndpoint } from "../reducers/syncCollectionEdX"
import { potentialCollectionOwnersEndpoint } from "../reducers/potentialCollectionOwners"

export const endpoints = [
  collectionsListEndpoint,
  collectionsEndpoint,
  uploadVideoEndpoint,
  videosEndpoint,
  videoSubtitlesEndpoint,
  syncCollectionEdXEndpoint,
  potentialCollectionOwnersEndpoint
]
