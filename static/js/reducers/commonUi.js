// @flow
import type { Action } from '../flow/reduxTypes';

import {
  SET_DRAWER_OPEN
} from '../actions/commonUi';

export type CommonUiState = {
  drawerOpen: boolean
};

export const INITIAL_UI_STATE = {
  drawerOpen: false
};

const reducer = (state: CommonUiState = INITIAL_UI_STATE, action: Action<any, null>) => {
  switch (action.type) {
  case SET_DRAWER_OPEN:
    return {...state, drawerOpen: action.payload };
  default:
    return state;
  }
};

export default reducer;
