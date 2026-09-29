import type { Video } from "./videoTypes"
import type { User } from "./userTypes"
import type { DescriptionFormat } from "./descriptionTypes"

export type CollectionListItem = {
  key: string
  // In the serializer's `fields` tuple (ui/serializers.py:418) and returned on
  // every collection, but absent from the Flow type. Video declared it; this
  // did not.
  created_at: string
  title: string
  description: string | null
  description_format: DescriptionFormat
  view_lists: Array<string>
  admin_lists: Array<string>
  is_logged_in_only: boolean
  video_count: number
  edx_course_id: string | null
  // ui/serializers.py:354-355: `owner` is a PrimaryKeyRelatedField, so it is
  // the user's id, and `owner_info` is UserSerializer(source="owner"). The
  // Flow type had `owner: User` and no owner_info at all, while
  // CollectionDetailPage, CollectionListPage and factories/collection all
  // read collection.owner_info.username.
  owner: number
  owner_info: User
  is_public: boolean
  // ui/models.py:217 declares stream_source null=True, blank=True, so it is
  // null on every collection that has not chosen a source.
  stream_source: string | null
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
  // Written by makeInitializedForm and read by nothing. Declared because they
  // really are in the form state at runtime; deleting them is a behaviour
  // change and belongs in its own commit, not a type migration.
  videoCount?: number
  ownerInfo?: User
}

/*
 * The subset of a collection that makeInitializedForm reads.
 *
 * Separate from CollectionListItem because the "no collection yet" branch
 * synthesises one, and `is_public` and `stream_source` -- which a real
 * CollectionListItem always carries -- are neither available nor read on that
 * path. A real CollectionListItem is assignable to this.
 */
export type CollectionFormSource = {
  key: string
  title: string
  description: string | null
  description_format: DescriptionFormat
  view_lists: Array<string>
  admin_lists: Array<string>
  is_logged_in_only: boolean
  edx_course_id: string | null
  video_count: number
  owner: number | null
  owner_info: User
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
