import type { Video } from "./videoTypes"
import type { User } from "./userTypes"
import type { DescriptionFormat } from "./descriptionTypes"

export type CollectionListItem = {
  key: string
  title: string
  description: string | null
  description_format: DescriptionFormat
  view_lists: Array<string>
  admin_lists: Array<string>
  is_logged_in_only: boolean
  video_count: number
  edx_course_id: string | null
  owner: User
  is_public: boolean
  stream_source: string
}

export type Collection = CollectionListItem & {
  videos: Array<Video>
  is_admin: boolean
  is_edx_course_admin: boolean
}

export type CollectionList = Array<CollectionListItem>

export type CollectionFormState = {
  key: string | null
  title: string | null
  description: string | null
  description_format: DescriptionFormat | null
  viewChoice: string
  viewLists: string | null
  adminChoice: string
  adminLists: string | null
  edxCourseId: string | null
  ownerId: number | null
}

export type CollectionValidation = {
  title?: string
  view_lists?: string
  admin_lists?: string
  edx_course_id?: string
}

export type CollectionUiState = {
  newCollectionForm: CollectionFormState
  editCollectionForm: CollectionFormState
  isNew: boolean
  selectedVideoKey: string | null
  errors?: CollectionValidation
}

export type CollectionsPage = {
  collections: Array<Collection>
  status: string
}

export type CollectionsPagination = {
  count: number
  currentPage: number
  currentPageData?: CollectionsPage
  numPages?: number
  pages: {
    [key: string]: CollectionsPage
  }
  setCurrentPage?: (nextCurrentPage: number) => void
}
