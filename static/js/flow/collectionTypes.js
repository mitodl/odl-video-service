// @flow

import type { Video } from './videoTypes';

export type CollectionListItem = {
  key:                string,
  title:              string,
  description:        ?string,
  view_lists:         Array<string>,
  admin_lists:        Array<string>
};

export type Collection = CollectionListItem & {
  videos:             Array<Video>,
  is_admin:           boolean
};

export type CollectionList = Array<CollectionListItem>;
