import type { Dispatch, Reducer, UnknownAction } from "redux"
import type { ThunkDispatch } from "redux-thunk"

// redux's Flow libdef exported a `State` type; its TypeScript types do not,
// because application state is the app's own concern. Ours is RootState.
import type { RootState } from "./rootState"

export type State = RootState

/*
 * The dispatch a connected component actually receives. redux's bare `Dispatch`
 * rejects a thunk, and every async action creator here returns one, so a
 * component typed with plain Dispatch cannot dispatch its own actions.
 * Declared once here because two dialogs had each grown their own identical
 * copy.
 */
export type AppDispatch = ThunkDispatch<RootState, unknown, UnknownAction>

export type ActionType = string

export type Action<payload, meta> = {
  type: ActionType
  payload: payload
  meta: meta
}

export type Dispatcher<T> = (d: Dispatch) => Promise<T>

export type AsyncActionHelper = (...a: any[]) => Promise<any>

export type ActionCreator = (...a: any[]) => Action<any, null>

export type AsyncActionCreator<T> = (...a: any[]) => Dispatcher<T>

export type AssertReducerResultState<T> = (
  actionFunc: () => Action<any, any>,
  stateFunc: (reducerState: State) => T,
  defaultValue: any
) => void

export type TestStore = {
  dispatch: Dispatch
  getState: () => State
  subscribe: (listener: () => void) => () => void
  replaceReducer: (reducer: Reducer<any, any>) => void
}
