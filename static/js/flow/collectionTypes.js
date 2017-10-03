// @flow

import type { Video } from './videoTypes';

export type CollectionListItem = {
  key:                string,
  title:              string,
  description:        ?string,
  view_lists:         Array<string>,
  admin_lists:        Array<string>,
  video_count:        number
};

export type Collection = CollectionListItem & {
  videos:             Array<Video>,
  is_admin:           boolean
};

export type CollectionList = Array<CollectionListItem>;

export type CollectionFormState = {
  key: ?string,
  title: ?string,
  description: ?string,
  viewChoice: string,
  viewLists: ?string,
  adminChoice: string,
  adminLists: ?string,
};

export type CollectionUiState = {
  newCollectionForm: CollectionFormState,
  editCollectionForm: CollectionFormState,
  isNew: boolean,
  selectedVideoKey: ?string
};
