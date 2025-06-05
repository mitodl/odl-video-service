// @flow
import { GET, INITIAL_STATE } from "redux-hammock/constants"

import * as api from "../lib/api"

import type { User } from "../flow/userTypes"

export const usersListEndpoint = {
  name:              "usersList",
  verbs:             [GET],
  initialState:      { ...INITIAL_STATE, data: [] },
  getFunc:           (): Promise<{users: Array<User>}> => api.getUsers(),
}
