import { deriveActions } from "redux-hammock"

import { endpoints } from "../lib/redux_rest"

import * as collectionsPagination from "./collectionsPagination"
import * as videoUi from "./videoUi"
import * as toast from "./toast"

/*
 * redux-hammock ships no type declarations. deriveActions returns one
 * thunk-creator per verb the endpoint declares (get/post/patch) plus whatever
 * it lists in extraActions, so the slice is keyed by name rather than spelled
 * out per endpoint.
 */
type RestActions = Record<string, (...args: any[]) => any>

/*
 * Spelled out rather than left as Record<string, unknown>: consumers reach
 * straight through this object (`actions.videoUi.setEditVideoTitle`,
 * `actions.videos.patch`), and an index signature of `unknown` makes every one
 * of those an error. The eight REST slices are exactly the `endpoints` array
 * in lib/redux_rest -- keep the two in step.
 */
type Actions = {
  collectionsPagination: typeof collectionsPagination.actionCreators
  videoUi: typeof videoUi.actionCreators
  toast: typeof toast.actionCreators
  collectionsList: RestActions
  collections: RestActions
  uploadVideo: RestActions
  videos: RestActions
  videoSubtitles: RestActions
  videoAnalytics: RestActions
  syncCollectionEdX: RestActions
  potentialCollectionOwners: RestActions
}

const actions = {
  collectionsPagination: collectionsPagination.actionCreators,
  videoUi:               videoUi.actionCreators,
  toast:                 toast.actionCreators
} as Actions

endpoints.forEach(endpoint => {
  actions[endpoint.name as keyof Actions] = deriveActions(endpoint)
})

export { actions }
