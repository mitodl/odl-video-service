// @flow
import type { Action } from '../flow/reduxTypes';
import {
  SHOW_DIALOG,
  HIDE_DIALOG,
  SET_DRAWER_OPEN
} from '../actions/commonUi';
import { DIALOGS } from '../constants';
import { showDialog, hideDialog } from '../lib/dialog';

import type { DialogVisibilityState } from '../lib/dialog';

export type CommonUiState = DialogVisibilityState & {
  drawerOpen: boolean
};

export const INITIAL_UI_STATE = {
  drawerOpen: false,
  dialogVisibility: {
    [DIALOGS.NEW_COLLECTION]: false
  }
};

const reducer = (state: CommonUiState = INITIAL_UI_STATE, action: Action<any, null>) => {
  switch (action.type) {
  case SET_DRAWER_OPEN:
    return {...state, drawerOpen: action.payload };
  case SHOW_DIALOG:
    return showDialog(state, action.payload);
  case HIDE_DIALOG:
    return hideDialog(state, action.payload);
  default:
    return state;
  }
};

export default reducer;
