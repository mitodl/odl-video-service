// @flow
import casual from 'casual-browserify';

import { makeVideos } from './video';
import { makeCounter } from "../util/test_utils";

import type { Collection } from "../flow/collectionTypes";

const ownerId = makeCounter();

export const makeCollection = (collectionKey: string = casual.uuid): Collection => ({
  key: collectionKey,
  created_at: casual.moment.format(),
  title: casual.text,
  description: casual.text,
  owner: ownerId(),
  videos: makeVideos(2),
  view_lists: casual.array_of_words(2),
  admin_lists: casual.array_of_words(2)
});
