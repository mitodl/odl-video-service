import {
  compose,
  legacy_createStore as createStore,
  applyMiddleware
} from "redux"
import { thunk } from "redux-thunk" // Updated import
import { createLogger } from "redux-logger"

import rootReducer from "../reducers"
import type { RootState } from "../types/rootState"

const composeEnhancers =
  (typeof window !== "undefined" &&
    window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__) ||
  compose

let createStoreWithMiddleware
if (process.env.NODE_ENV !== "production") {
  createStoreWithMiddleware = composeEnhancers(
    applyMiddleware(thunk, createLogger())
  )(createStore)
} else {
  createStoreWithMiddleware = compose(applyMiddleware(thunk))(createStore)
}

// Partial: callers seed only the slices a test or page cares about, and
// combineReducers fills the rest from each reducer's own initial state.
export default function configureStore(initialState?: Partial<RootState>) {
  const store = createStoreWithMiddleware(rootReducer, initialState)

  if (module.hot) {
    // Enable Webpack hot module replacement for reducers
    module.hot.accept("../reducers", () => {
      // Use import() instead of require() for better code splitting
      import("../reducers").then(({ default: nextRootReducer }) => {
        store.replaceReducer(nextRootReducer)
      })
    })
  }

  return store
}
