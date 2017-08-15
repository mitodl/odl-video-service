// @flow
import type { Action } from '../flow/reduxTypes';

import {
  SET_DIALOG_VISIBILITY,
  SET_DRAWER_OPEN,
  SET_TITLE,
  SET_DESCRIPTION,
  CLEAR_DIALOG,
} from '../actions/videoDetailUi';

export type VideoDetailUIState = {
  dialog: {
    visible: boolean,
    title: string,
    description: string,
  },
  drawerOpen: boolean,
};

export const INITIAL_UI_STATE = {
  dialog: {
    visible: false,
    title: '',
    description: '',
  },
  drawerOpen: false,
};

const reducer = (state: VideoDetailUIState = INITIAL_UI_STATE, action: Action<any, null>) => {
  switch (action.type) {
  case SET_DIALOG_VISIBILITY:
    return {...state, dialog: {...state.dialog, visible: action.payload }};
  case SET_TITLE:
    return {...state, dialog: {...state.dialog, title: action.payload }};
  case SET_DESCRIPTION:
    return {...state, dialog: {...state.dialog, description: action.payload }};
  case SET_DRAWER_OPEN:
    return {...state, drawerOpen: action.payload };
  case CLEAR_DIALOG:
    return {...state, dialog: INITIAL_UI_STATE.dialog };
  default:
    return state;
  }
};

export default reducer;
