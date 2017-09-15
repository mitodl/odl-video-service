// @flow
import casual from 'casual-browserify';

import { makeVideos } from './video';

import type { Collection } from "../flow/collectionTypes";

export const makeCollection = (collectionKey: string = casual.uuid): Collection => ({
  key: collectionKey,
  created_at: casual.moment.format(),
  title: casual.text,
  description: casual.text,
  videos: makeVideos(2),
  view_lists: casual.array_of_words(2),
  admin_lists: casual.array_of_words(2),
  is_admin: true
});
