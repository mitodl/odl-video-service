// @flow
import R from "ramda"
import _ from "lodash"

import {
  PERM_CHOICE_NONE,
  PERM_CHOICE_LISTS,
  PERM_CHOICE_LOGGED_IN
} from "../lib/dialog"
import type {
  Collection,
  CollectionFormState,
  CollectionListItem,
  CollectionUiState
} from "../flow/collectionTypes"
import type { RestState } from "../flow/restTypes"
import type {} from "../reducers/collectionUi"

export const getActiveCollectionDetail = (state: {
  collections?: ?RestState<Collection>
}): ?Collection =>
  state.collections && state.collections.data && state.collections.loaded ?
    state.collections.data :
    null

export const getVideoWithKey = (collection: Collection, key: string) =>
  R.compose(R.find(R.propEq("key", key)), R.defaultTo([]))(collection.videos)

export const getFormKey = (isNew: boolean): string =>
  isNew ? "newCollectionForm" : "editCollectionForm"

export const getCollectionForm = (
  state: CollectionUiState
): CollectionFormState => state[getFormKey(state.isNew)]

/**
 * Make an initialized form for use with existing collections
 */
export function makeInitializedForm(
  collection: ?CollectionListItem
): CollectionFormState {
  if (!collection) {
    collection = {
      key:               "",
      title:             "",
      description:       "",
      view_lists:        [],
      admin_lists:       [],
      is_logged_in_only: false,
      edx_course_id:     "",
      edx_endpoints:     [],
      video_count:       0,
      available_edx_endpoints: [],
    }
  }
  const viewChoice =
    collection.view_lists.length === 0 ? PERM_CHOICE_NONE : PERM_CHOICE_LISTS
  const adminChoice =
    collection.admin_lists.length === 0 ? PERM_CHOICE_NONE : PERM_CHOICE_LISTS

  return {
    key:         collection.key,
    title:       collection.title,
    description: collection.description,
    viewChoice:  collection.is_logged_in_only ?
      PERM_CHOICE_LOGGED_IN :
      viewChoice,
    viewLists:   _.join(collection.view_lists, ","),
    adminChoice: adminChoice,
    adminLists:  _.join(collection.admin_lists, ","),
    edxCourseId: collection.edx_course_id,
    edxEndpoint: collection.edx_endpoints[0],
    videoCount:  collection.video_count
  }
}
