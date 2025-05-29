// @flow
import { combineReducers } from "redux"
import { deriveReducers } from "redux-hammock"

import { actions } from "../actions"
import { endpoints } from "../lib/redux_rest"
import commonUi from "./commonUi"
import collectionsPagination from "./collectionsPagination"
import collectionUi from "./collectionUi"
import videoUi from "./videoUi"
import toast from "./toast"
import edxEndpoints from "./edxEndpoints"

const reducers: Object = {
  collectionsPagination,
  edxEndpoints,
  commonUi,
  collectionUi,
  videoUi,
  toast,
}
endpoints.forEach(endpoint => {
  reducers[endpoint.name] = deriveReducers(endpoint, actions[endpoint.name])
})

export default combineReducers({
  ...reducers
})
