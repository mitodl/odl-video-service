// @flow
import {
  collectionsListEndpoint,
  collectionsEndpoint,
  uploadVideoEndpoint
} from '../reducers/collections';
import { videosEndpoint } from '../reducers/videos';
import { videoSubtitlesEndpoint } from '../reducers/videoSubtitles';

export const endpoints = [
  collectionsListEndpoint,
  collectionsEndpoint,
  uploadVideoEndpoint,
  videosEndpoint,
  videoSubtitlesEndpoint
];
