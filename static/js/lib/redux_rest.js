// @flow
import {
  collectionsListEndpoint,
  collectionsEndpoint,
  uploadVideoEndpoint
} from '../reducers/collections';
import { videosEndpoint } from '../reducers/videos';

export const endpoints = [
  collectionsListEndpoint,
  collectionsEndpoint,
  uploadVideoEndpoint,
  videosEndpoint,
];
