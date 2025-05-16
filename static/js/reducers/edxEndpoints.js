// @flow
import type { Action } from "../flow/reduxTypes"
import { constants } from "../actions/edxEndpoints"
import type { EdxEndpointList } from "../flow/collectionTypes"

export type EdxEndpointsState = {
  data:   ?EdxEndpointList,
  error:  ?Object,
  status: string
}

const INITIAL_STATE = {
  data:   null,
  error:  null,
  status: "INITIAL"
}

const reducer = (state: EdxEndpointsState = INITIAL_STATE, action: Action) => {
  switch (action.type) {
  case constants.REQUEST_GET_ENDPOINTS:
    return {
      ...state,
      status: "LOADING"
    }
  case constants.RECEIVE_GET_ENDPOINTS_SUCCESS:
    return {
      ...state,
      data:   action.payload.endpoints,
      status: "LOADED"
    }
  case constants.RECEIVE_GET_ENDPOINTS_FAILURE:
    return {
      ...state,
      error:  action.payload.error,
      status: "ERROR"
    }
  default:
    return state
  }
}

export default reducer
