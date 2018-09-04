// @flow
import _ from "lodash"
import type { Action } from "../flow/reduxTypes"
import type { ToastState } from "../flow/toastTypes"

import { constants } from "../actions/toast"

export const INITIAL_TOAST_STATE = {
  messages: []
}

const reducer = (
  state: ToastState = INITIAL_TOAST_STATE,
  action: Action<any, null>
) => {
  switch (action.type) {
  case constants.ADD_MESSAGE:
    return {
      ...state,
      messages: [...state.messages, action.payload.message]
    }
  case constants.REMOVE_MESSAGE:
    return {
      ...state,
      messages: _.filter(state.messages, message => {
        return message.key !== action.payload.key
      })
    }
  default:
    return state
  }
}

export default reducer
