// @flow
import { createAction } from "redux-actions"
import type { Dispatch } from "redux"
import * as api from "../lib/api"


const qualifiedName = (name: string) => `COLLECTIONS_PAGINATION_${name}`
const constants = {}
const actionCreators = {}

constants.REQUEST_GET_PAGE = qualifiedName("REQUEST_GET_PAGE")
actionCreators.requestGetPage = createAction(
  constants.REQUEST_GET_PAGE)

constants.RECEIVE_GET_PAGE_SUCCESS = qualifiedName("RECEIVE_GET_PAGE_SUCCESS")
actionCreators.receiveGetPageSuccess = createAction(
  constants.RECEIVE_GET_PAGE_SUCCESS)

constants.RECEIVE_GET_PAGE_FAILURE = qualifiedName("RECEIVE_GET_PAGE_FAILURE")
actionCreators.receiveGetPageFailure = createAction(
  constants.RECEIVE_GET_PAGE_FAILURE)

actionCreators.getPage = (page: number) => {
  const thunk = async (dispatch: Dispatch) => {
    dispatch(actionCreators.requestGetPage({page}))
    try {
      const response = await api.getCollections({page})
      const data  = response.data || {}
      const collections = data.results || []
      const count = data.count
      // DISPATCH RECEIVE_COLLECTIONS HERE
      dispatch(actionCreators.receiveGetPageSuccess({
        page,
        count,
        entityKeys: (
          collections.map((collection) => collection.key)
        ),
      }))
    } catch (error) {
      dispatch(actionCreators.receiveGetPageFailure({
        page,
        error
      }))
    }
  }
  return thunk
}

export { actionCreators, constants }
