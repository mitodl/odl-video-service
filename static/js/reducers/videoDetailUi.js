// @flow
import type { Action } from '../flow/reduxTypes';

import {
  SET_EDIT_DIALOG_VISIBILITY,
  SET_DRAWER_OPEN,
  SET_TITLE,
  SET_DESCRIPTION,
  CLEAR_EDIT_DIALOG,
  SET_SHARE_DIALOG_VISIBILITY,
  CLEAR_SHARE_DIALOG
} from '../actions/videoDetailUi';

export type VideoDetailUIState = {
  editDialog: {
    visible: boolean,
    title: string,
    description: string,
  },
  shareDialog: {
    visible: boolean,
  },
  drawerOpen: boolean,
};

export const INITIAL_UI_STATE = {
  editDialog: {
    visible: false,
    title: '',
    description: '',
  },
  shareDialog: {
    visible: false,
  },
  drawerOpen: false,
};

const reducer = (state: VideoDetailUIState = INITIAL_UI_STATE, action: Action<any, null>) => {
  switch (action.type) {
  case SET_EDIT_DIALOG_VISIBILITY:
    return {...state, editDialog: {...state.editDialog, visible: action.payload }};
  case SET_TITLE:
    return {...state, editDialog: {...state.editDialog, title: action.payload }};
  case SET_DESCRIPTION:
    return {...state, editDialog: {...state.editDialog, description: action.payload }};
  case SET_DRAWER_OPEN:
    return {...state, drawerOpen: action.payload };
  case CLEAR_EDIT_DIALOG:
    return {...state, editDialog: INITIAL_UI_STATE.editDialog };
  case SET_SHARE_DIALOG_VISIBILITY:
    return {...state, shareDialog: {...state.shareDialog, visible: action.payload }};
  case CLEAR_SHARE_DIALOG:
    return {...state, shareDialog: INITIAL_UI_STATE.shareDialog };
  default:
    return state;
  }
};

export default reducer;
