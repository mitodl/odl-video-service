// @flow
import type { Action } from '../flow/reduxTypes';

import {
  INIT_COLLECTION_FORM,
  SET_COLLECTION_TITLE,
  SET_COLLECTION_DESC,
  SET_VIEW_CHOICE,
  SET_VIEW_LISTS,
  SET_ADMIN_CHOICE,
  SET_ADMIN_LISTS,
  SET_SELECTED_VIDEO_KEY,
  SET_IS_NEW,
} from '../actions/collectionUi';
import { PERM_CHOICE_NONE } from '../lib/dialog';

export type CollectionFormState = {
  key: ?string,
  title: ?string,
  description: ?string,
  viewChoice: string,
  viewLists: ?string,
  adminChoice: string,
  adminLists: ?string,
};

export type CollectionUiState = {
  newCollectionForm: CollectionFormState,
  editCollectionForm: CollectionFormState,
  isNew: boolean,
  selectedVideoKey: ?string
};

export const INITIAL_COLLECTION_FORM_STATE = {
  key: '',
  title: '',
  description: '',
  viewChoice: PERM_CHOICE_NONE,
  viewLists: null,
  adminChoice: PERM_CHOICE_NONE,
  adminLists: null,
};

export const INITIAL_UI_STATE = {
  newCollectionForm: INITIAL_COLLECTION_FORM_STATE,
  editCollectionForm: INITIAL_COLLECTION_FORM_STATE,
  isNew: true,
  selectedVideoKey: null
};

const getFormKey = (isNew: boolean): string => isNew ? "newCollectionForm" : "editCollectionForm";

export const getCollectionForm = (
  state: CollectionUiState
): CollectionFormState => state[getFormKey(state.isNew)];

const updateCollectionForm = (state: CollectionUiState, key: string, newValue: ?string) => ({
  ...state,
  [getFormKey(state.isNew)]: {
    ...state[getFormKey(state.isNew)],
    [key]: newValue
  }
});

const reducer = (state: CollectionUiState = INITIAL_UI_STATE, action: Action<any, null>) => {
  switch (action.type) {
  case INIT_COLLECTION_FORM:
    return {
      ...state,
      [getFormKey(state.isNew)]: {
        ...state[getFormKey(state.isNew)],
        ...action.payload
      }
    };
  case SET_COLLECTION_TITLE:
    return updateCollectionForm(state, 'title', action.payload);
  case SET_COLLECTION_DESC:
    return updateCollectionForm(state, 'description', action.payload);
  case SET_VIEW_CHOICE:
    return updateCollectionForm(state, 'viewChoice', action.payload);
  case SET_VIEW_LISTS:
    return updateCollectionForm(state, 'viewLists', action.payload);
  case SET_ADMIN_CHOICE:
    return updateCollectionForm(state, 'adminChoice', action.payload);
  case SET_ADMIN_LISTS:
    return updateCollectionForm(state, 'adminLists', action.payload);
  case SET_SELECTED_VIDEO_KEY:
    return {...state, selectedVideoKey: action.payload};
  case SET_IS_NEW:
    return { ...state, isNew: action.payload };
  default:
    return state;
  }
};

export default reducer;
