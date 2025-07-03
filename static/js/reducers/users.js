// @flow
import { GET, INITIAL_STATE } from "redux-hammock/constants"

import * as api from "../lib/api"

import type { User } from "../flow/userTypes"

export const potentialCollectionOwnersEndpoint = {
  name:              "potentialCollectionOwners",
  verbs:             [GET],
  initialState:      { ...INITIAL_STATE, data: [] },
  getFunc:           (collectionKey: string): Promise<{users: Array<User>}> => api.getPotentialCollectionOwners(collectionKey),
}
