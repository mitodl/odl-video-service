// @flow

import type { Video } from './videoTypes';

type CollectionListItem = {
  key:                string,
  title:              string,
  description:        ?string,
  owner:              number,
  view_lists:         Array<string>,
  admin_lists:        Array<string>
};

export type Collection = CollectionListItem & {
  videos:             Array<Video>,
  is_admin:           boolean
};

export type CollectionList = Array<CollectionListItem>;
