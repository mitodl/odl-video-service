// @flow
import type { Action } from "../flow/reduxTypes";
import {
  SHOW_DIALOG,
  HIDE_DIALOG,
  SET_DRAWER_OPEN,
  INIT_EDIT_VIDEO_FORM,
  SET_EDIT_VIDEO_TITLE,
  SET_EDIT_VIDEO_DESC,
  SHOW_MENU,
  HIDE_MENU,
  TOGGLE_FAQ_VISIBILITY
} from "../actions/commonUi";
import { DIALOGS } from "../constants";
import { showDialog, hideDialog } from "../lib/dialog";

import type { DialogVisibilityState } from "../lib/dialog";

export type CommonUiState = DialogVisibilityState & {
  drawerOpen: boolean,
  editVideoForm: {
    key: ?string,
    title: string,
    description: string
  },
  menuVisibility: {
    [string]: boolean
  },
  FAQVisibility: Map<string, boolean>
}

export const INITIAL_EDIT_VIDEO_FORM_STATE = {
  key: null,
  title: "",
  description: ""
};

export const INITIAL_UI_STATE = {
  dialogVisibility: {
    [DIALOGS.COLLECTION_FORM]: false,
    [DIALOGS.SHARE_VIDEO]: false,
    [DIALOGS.EDIT_VIDEO]: false
  },
  drawerOpen: false,
  menuVisibility: {},
  editVideoForm: INITIAL_EDIT_VIDEO_FORM_STATE,
  FAQVisibility: new Map()
};

const reducer = (state: CommonUiState = INITIAL_UI_STATE, action: Action<any, null>) => {
  switch (action.type) {
  case SET_DRAWER_OPEN:
    return { ...state, drawerOpen: action.payload };
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
    return { ...state, editVideoForm: { ...state.editVideoForm, title: action.payload } };
  case SET_EDIT_VIDEO_DESC:
    return { ...state, editVideoForm: { ...state.editVideoForm, description: action.payload } };
  case SHOW_MENU:
    return {
      ...state,
      menuVisibility: {
        ...state.menuVisibility,
        [action.payload]: true
      }
    };
  case HIDE_MENU:
    return {
      ...state,
      menuVisibility: {
        ...state.menuVisibility,
        [action.payload]: false
      }
    };
  case TOGGLE_FAQ_VISIBILITY: // eslint-disable-line no-case-declarations
    let update = new Map(state.FAQVisibility);
    update.set(action.payload, !update.get(action.payload));
    return {
      ...state,
      FAQVisibility: update
    };
  default:
    return state;
  }
};

export default reducer;
