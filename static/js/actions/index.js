// @flow
import { deriveActions } from "redux-hammock"

import { endpoints } from "../lib/redux_rest"

import * as collectionsPagination from "./collectionsPagination"
import * as videoUi from "./videoUi"
import * as toast from "./toast"

const actions: Object = {
  collectionsPagination: collectionsPagination.actionCreators,
  videoUi:               videoUi.actionCreators,
  toast:                 toast.actionCreators
}

endpoints.forEach(endpoint => {
  actions[endpoint.name] = deriveActions(endpoint)
})

export { actions }
