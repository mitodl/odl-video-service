// @flow
import { createAction } from "redux-actions"
import type { Dispatch } from "redux"
import * as api from "../lib/api"

const qualifiedName = (name: string) => `EDX_ENDPOINTS_${name}`
const constants = {}
const actionCreators = {}

constants.REQUEST_GET_ENDPOINTS = qualifiedName("REQUEST_GET_ENDPOINTS")
actionCreators.requestGetEndpoints = createAction(constants.REQUEST_GET_ENDPOINTS)

constants.RECEIVE_GET_ENDPOINTS_SUCCESS = qualifiedName("RECEIVE_GET_ENDPOINTS_SUCCESS")
actionCreators.receiveGetEndpointsSuccess = createAction(
  constants.RECEIVE_GET_ENDPOINTS_SUCCESS
)

constants.RECEIVE_GET_ENDPOINTS_FAILURE = qualifiedName("RECEIVE_GET_ENDPOINTS_FAILURE")
actionCreators.receiveGetEndpointsFailure = createAction(
  constants.RECEIVE_GET_ENDPOINTS_FAILURE
)

actionCreators.getEndpoints = () => {
  const thunk = async (dispatch: Dispatch) => {
    dispatch(actionCreators.requestGetEndpoints())
    try {
      const response = await api.getEdxEndpoints()
      dispatch(
        actionCreators.receiveGetEndpointsSuccess({
          endpoints: response
        })
      )
      return response
    } catch (error) {
      dispatch(
        actionCreators.receiveGetEndpointsFailure({
          error
        })
      )
    }
  }
  return thunk
}

export { actionCreators, constants }
