// @flow

import type { Video } from './videoTypes'

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

export type CollectionValidation = {
  title?:  string,
  view_lists?: string,
  admin_lists?: string
}

export type CollectionUiState = {
  newCollectionForm: CollectionFormState,
  editCollectionForm: CollectionFormState,
  isNew: boolean,
  selectedVideoKey: ?string,
  errors?: CollectionValidation
};

export type CollectionsPage = {
  collections: Array<Collection>,
  status: string,
}

export type CollectionsPagination = {
  count: number,
  currentPage: number,
  currentPageData?: CollectionsPage,
  numPages?: number,
  pages: {
    [string|number]: CollectionsPage,
  },
  setCurrentPage?: (nextCurrentPage: number) => void,
}
