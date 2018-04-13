// @flow
import type { Action } from "../flow/reduxTypes"

import { constants } from "../actions/collectionsPagination"

export const INITIAL_COLLECTIONS_PAGINATION_STATE = {
  count:       0,
  currentPage: 1,
  pages:       {},
}

const generateInitialPageState = () => ({
  status:      null,
  collections: [],
})

const reducer = (
  state = INITIAL_COLLECTIONS_PAGINATION_STATE,
  action: Action<any, null>
) => {
  switch (action.type) {
  case constants.REQUEST_GET_PAGE:
    return {
      ...state,
      pages: {
        ...state.pages,
        [action.payload.page]: {
          ...generateInitialPageState(),
          status: 'LOADING',
        }
      }
    }
  case constants.RECEIVE_GET_PAGE_SUCCESS:
    return {
      ...state,
      count:     action.payload.count,
      numPages: action.payload.numPages,
      pages:     {
        ...state.pages,
        [action.payload.page]: {
          ...state.pages[action.payload.page],
          collections: action.payload.collections,
          startIndex:  action.payload.startIndex,
          endIndex:    action.payload.endIndex,
          status:      'LOADED',
        }
      }
    }
  case constants.RECEIVE_GET_PAGE_FAILURE:
    return {
      ...state,
      pages: {
        ...state.pages,
        [action.payload.page]: {
          ...state.pages[action.payload.page],
          status: 'ERROR',
          error:  action.payload.error,
        }
      }
    }
  case constants.SET_CURRENT_PAGE:
    return {
      ...state,
      currentPage: action.payload.currentPage,
    }
  default:
    return state
  }
}

export default reducer
