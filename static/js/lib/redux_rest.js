// @flow
import { collectionsListEndpoint, collectionsEndpoint } from '../reducers/collections';
import { videosEndpoint } from '../reducers/videos';

export const endpoints = [
  collectionsListEndpoint,
  collectionsEndpoint,
  videosEndpoint,
];
