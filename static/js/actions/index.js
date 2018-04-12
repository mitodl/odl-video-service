// @flow
import { deriveActions } from "redux-hammock"

import { endpoints } from "../lib/redux_rest"

import * as collectionsPagination from './collectionsPagination'

const actions: Object = {
  collectionsPagination: collectionsPagination.actionCreators,
}
endpoints.forEach(endpoint => {
  actions[endpoint.name] = deriveActions(endpoint)
})

export { actions }
