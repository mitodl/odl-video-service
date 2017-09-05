// @flow
import { GET, INITIAL_STATE } from "redux-hammock/constants";

import * as api from "../lib/api";
import type { Collection } from "../flow/collectionTypes";

export const collectionsListEndpoint = {
  name:              "collectionsList",
  verbs:             [GET],
  initialState:      { ...INITIAL_STATE, data: [] },
  getFunc:           () => api.getCollections()
};

export const collectionsEndpoint = {
  name: "collections",
  verbs: [GET],
  initialState: { ...INITIAL_STATE, data: new Map() },
  getFunc: (collectionKey: string): Promise<Collection> => api.getCollection(collectionKey)
};
