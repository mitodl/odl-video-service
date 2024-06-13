// @flow
import { GET, PATCH, POST, INITIAL_STATE } from "redux-hammock/constants"
import * as R from "ramda"

import * as api from "../lib/api"
import type { Collection, CollectionList } from "../flow/collectionTypes"
import { CLEAR_COLLECTION_ERRORS } from "../actions/collectionUi"

export const collectionsListEndpoint = {
  name:               "collectionsList",
  verbs:              [GET, POST],
  initialState:       { ...INITIAL_STATE, data: [] },
  getFunc:            (): Promise<CollectionList> => api.getCollections(),
  postFunc:           (collection: Collection) => api.createCollection(collection),
  postSuccessHandler: (payload: Collection, data: Object) => {
    return { results: [payload, ...(data ? data.results || [] : [])] }
  }
}

export const collectionsEndpoint = {
  name:         "collections",
  verbs:        [GET, PATCH],
  initialState: { ...INITIAL_STATE, data: new Map() },
  getFunc:      (collectionKey: string): Promise<Collection> =>
    api.getCollection(collectionKey),
  patchFunc: (collectionKey: string, payload: Object): Promise<Collection> =>
    api.updateCollection(collectionKey, payload),
  extraActions: {
    [CLEAR_COLLECTION_ERRORS]: R.dissoc("error")
  }
}

export const uploadVideoEndpoint = {
  name:         "uploadVideo",
  verbs:        [POST],
  initialState: { ...INITIAL_STATE },
  postFunc:     (collectionKey: string, files: Array<Object>): Promise<Object> =>
    api.uploadVideo(collectionKey, files)
}
