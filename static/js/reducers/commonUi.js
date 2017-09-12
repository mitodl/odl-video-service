// @flow
import type { Action } from '../flow/reduxTypes';
import {
  SHOW_DIALOG,
  HIDE_DIALOG,
  SET_DRAWER_OPEN,
  INIT_EDIT_VIDEO_FORM,
  SET_EDIT_VIDEO_TITLE,
  SET_EDIT_VIDEO_DESC
} from '../actions/commonUi';
import { DIALOGS } from '../constants';
import { showDialog, hideDialog } from '../lib/dialog';

import type { DialogVisibilityState } from '../lib/dialog';

export type CommonUiState = DialogVisibilityState & {
  drawerOpen: boolean,
  editVideoForm: {
    key: ?string,
    title: string,
    description: string
  }
};

export const INITIAL_EDIT_VIDEO_FORM_STATE = {
  key: null,
  title: '',
  description: ''
};

export const INITIAL_UI_STATE = {
  dialogVisibility: {
    [DIALOGS.NEW_COLLECTION]: false
  },
  drawerOpen: false,
  editVideoForm: INITIAL_EDIT_VIDEO_FORM_STATE
};

const reducer = (state: CommonUiState = INITIAL_UI_STATE, action: Action<any, null>) => {
  switch (action.type) {
  case SET_DRAWER_OPEN:
    return {...state, drawerOpen: action.payload };
  case SHOW_DIALOG:
    return showDialog(state, action.payload);
  case HIDE_DIALOG:
    return hideDialog(state, action.payload);
  case INIT_EDIT_VIDEO_FORM:
    return {
      ...state,
      editVideoForm: {
        ...state.editVideoForm,
        ...action.payload
      }
    };
  case SET_EDIT_VIDEO_TITLE:
    return {...state, editVideoForm: { ...state.editVideoForm, title: action.payload }};
  case SET_EDIT_VIDEO_DESC:
    return {...state, editVideoForm: { ...state.editVideoForm, description: action.payload }};
  default:
    return state;
  }
};

export default reducer;
