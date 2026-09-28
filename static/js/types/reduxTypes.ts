import type { Dispatch, Reducer } from "redux"

// redux's Flow libdef exported a `State` type; its TypeScript types do not,
// because application state is the app's own concern. Nothing here constrains
// it today, so it stays open until the reducers are converted.
export type State = Record<string, any>

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
