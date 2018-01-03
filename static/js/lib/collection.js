// @flow
import R from "ramda"
import _ from "lodash"

import { PERM_CHOICE_NONE, PERM_CHOICE_LISTS } from "../lib/dialog"
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
  state.collections && state.collections.data && state.collections.loaded
    ? state.collections.data
    : null

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
      key:         "",
      title:       "",
      description: "",
      view_lists:  [],
      admin_lists: [],
      video_count: 0
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
    viewChoice:  viewChoice,
    viewLists:   _.join(collection.view_lists, ","),
    adminChoice: adminChoice,
    adminLists:  _.join(collection.admin_lists, ","),
    videoCount:  collection.video_count
  }
}
