// @flow

import type { Video } from './videoTypes'

export type EdxEndpoint = {
  id: number,
  name: string,
  base_url: string,
  edx_video_api_path: string,
  is_global_default: boolean,
  created_at: string,
  updated_at: string,
};

export type EdxEndpointList = Array<EdxEndpoint>;

export type CollectionListItem = {
  key:                string,
  title:              string,
  description:        ?string,
  view_lists:         Array<string>,
  admin_lists:        Array<string>,
  is_logged_in_only:  boolean,
  video_count:        number,
  edx_course_id:      ?string
};

export type Collection = CollectionListItem & {
  videos:              Array<Video>,
  is_admin:            boolean,
  is_edx_course_admin: boolean,
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
  edxCourseId: ?string,
};

export type CollectionValidation = {
  title?:  string,
  view_lists?: string,
  admin_lists?: string,
  edx_course_id?: string
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
