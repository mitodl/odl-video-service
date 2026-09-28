import { createAction } from "redux-actions"
import type { Dispatch } from "redux"
import * as api from "../lib/api"
import type { PaginationParams } from "../lib/api"

const qualifiedName = (name: string) => `COLLECTIONS_PAGINATION_${name}`

/*
 * Declared as object literals rather than built by assigning onto `{}`.
 * The mutation style typechecked under Flow only because nothing was reading
 * these files; TypeScript infers `{}` from `const constants = {}` and rejects
 * every subsequent property. Literals also mean `constants.FOO` is checked at
 * every call site instead of resolving to `any`.
 */
export const constants = {
  REQUEST_GET_PAGE:         qualifiedName("REQUEST_GET_PAGE"),
  RECEIVE_GET_PAGE_SUCCESS: qualifiedName("RECEIVE_GET_PAGE_SUCCESS"),
  RECEIVE_GET_PAGE_FAILURE: qualifiedName("RECEIVE_GET_PAGE_FAILURE"),
  SET_CURRENT_PAGE:         qualifiedName("SET_CURRENT_PAGE")
}

const requestGetPage = createAction(constants.REQUEST_GET_PAGE)
const receiveGetPageSuccess = createAction(constants.RECEIVE_GET_PAGE_SUCCESS)
const receiveGetPageFailure = createAction(constants.RECEIVE_GET_PAGE_FAILURE)
const setCurrentPage = createAction(constants.SET_CURRENT_PAGE)

/*
 * Dispatches are routed through `actionCreators.x` rather than the local
 * bindings on purpose: collectionsPagination_test.js stubs these with
 * sandbox.stub(actionCreators, "requestGetPage"), which replaces the property
 * on the exported object. Calling the local binding would bypass the stub and
 * silently defeat those tests.
 */
const getPage = (opts: { page: number }) => {
  const { page } = opts
  const thunk = async (dispatch: Dispatch) => {
    // Get filters from URL parameters
    const params = new URLSearchParams(window.location.search)
    const searchQuery = params.get("search")
    // Construct query parameters
    const queryParams: PaginationParams & { search?: string } = { page }
    if (searchQuery) queryParams.search = searchQuery

    dispatch(actionCreators.requestGetPage({ page }))
    try {
      const response = await api.getCollections({ pagination: queryParams })
      // @TODO: ideally we would dispatch an action here to save collections to
      // a single place in state (e.g. state.collections).
      // However, it take a non-trivial refactor to implement this schema
      // change. So in the interest of scope, we store collections here.
      // This will likely be confusing for future developers, and I recommend
      // refactoring.
      dispatch(
        actionCreators.receiveGetPageSuccess({
          page,
          count:       response.count,
          collections: response.results,
          numPages:    response.num_pages,
          startIndex:  response.start_index,
          endIndex:    response.end_index
        })
      )
    } catch (error) {
      dispatch(
        actionCreators.receiveGetPageFailure({
          page,
          error
        })
      )
    }
  }
  return thunk
}

export const actionCreators = {
  requestGetPage,
  receiveGetPageSuccess,
  receiveGetPageFailure,
  setCurrentPage,
  getPage
}
