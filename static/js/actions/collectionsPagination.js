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
      // @TODO: ideally we would dispatch an action here to save collections to
      // a single place in state (e.g. state.collections).
      // However, it take a non-trivial refactor to implement this schema
      // change. So in the interest of scope, we store collections here.
      // This will likely be confusing for future developers, and I recommend
      // refactoring.
      dispatch(actionCreators.receiveGetPageSuccess({
        page,
        count:       (data.count || 0),
        collections: (data.results || []),
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
