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
 *
 * Each of those creators also carries the three action-type strings hammock
 * generated for it (hammock.js:159-161). Tests assert on them directly --
 * `listenForActions([actions.videos.get.requestType, ...])` -- so leaving them
 * off made every such assertion a type error.
 */
type RestAction = ((...args: any[]) => any) & {
  // Optional, not required: components narrow a slice with
  // `actions.collections as CollectionsActions`, and making these mandatory
  // destroys the structural overlap that cast depends on (TS2352).
  requestType?: string
  successType?: string
  failureType?: string
}

type RestActions = Record<string, RestAction>

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
