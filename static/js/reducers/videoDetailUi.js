// @flow
import type { Action } from '../flow/reduxTypes';

import {
  SET_SHARE_DIALOG_VISIBILITY,
  CLEAR_SHARE_DIALOG
} from '../actions/videoDetailUi';

export type VideoDetailUIState = {
  shareDialog: {
    visible: boolean,
  }
};

export const INITIAL_UI_STATE = {
  shareDialog: {
    visible: false,
  }
};

const reducer = (state: VideoDetailUIState = INITIAL_UI_STATE, action: Action<any, null>) => {
  switch (action.type) {
  case SET_SHARE_DIALOG_VISIBILITY:
    return {...state, shareDialog: {...state.shareDialog, visible: action.payload }};
  case CLEAR_SHARE_DIALOG:
    return {...state, shareDialog: INITIAL_UI_STATE.shareDialog };
  default:
    return state;
  }
};

export default reducer;
