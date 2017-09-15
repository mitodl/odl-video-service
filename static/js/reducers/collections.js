// @flow
import { GET, PATCH, POST, INITIAL_STATE } from "redux-hammock/constants";

import * as api from "../lib/api";
import type { Collection, CollectionList } from "../flow/collectionTypes";

export const collectionsListEndpoint = {
  name:              "collectionsList",
  verbs:             [GET],
  initialState:      { ...INITIAL_STATE, data: [] },
  getFunc:           (): Promise<CollectionList> => api.getCollections()
};

export const collectionsEndpoint = {
  name: "collections",
  verbs: [GET, PATCH],
  initialState: { ...INITIAL_STATE, data: new Map() },
  getFunc: (collectionKey: string): Promise<Collection> => api.getCollection(collectionKey),
  patchFunc: (collectionKey: string, payload: Object): Promise<Collection> => (
    api.updateCollection(collectionKey, payload)
  )
};

export const uploadVideoEndpoint = {
  name: "uploadVideo",
  verbs: [POST],
  initialState: { ...INITIAL_STATE },
  postFunc: (collectionKey: string, files: Array<Object>): Promise<Object> => (
    api.uploadVideo(collectionKey, files)
  )
};
