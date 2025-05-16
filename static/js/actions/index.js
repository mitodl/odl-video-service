// @flow
import { deriveActions } from "redux-hammock"

import { endpoints } from "../lib/redux_rest"

import * as collectionsPagination from "./collectionsPagination"
import * as videoUi from "./videoUi"
import * as toast from "./toast"
import * as edxEndpoints from "./edxEndpoints"

const actions: Object = {
  collectionsPagination: collectionsPagination.actionCreators,
  edxEndpoints:          edxEndpoints.actionCreators,
  videoUi:               videoUi.actionCreators,
  toast:                 toast.actionCreators,
}

endpoints.forEach(endpoint => {
  actions[endpoint.name] = deriveActions(endpoint)
})

export { actions }
