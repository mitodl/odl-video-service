// @flow
import type { Action } from '../flow/reduxTypes';

import {
  INIT_COLLECTION_FORM,
  CLEAR_COLLECTION_FORM,
  SET_COLLECTION_TITLE,
  SET_COLLECTION_DESC,
  SET_VIEW_CHOICE,
  SET_VIEW_LISTS,
  SET_ADMIN_CHOICE,
  SET_ADMIN_LISTS
} from '../actions/collectionUi';
import { PERM_CHOICE_NONE } from '../lib/dialog';

export type CollectionUiState = {
  collectionForm: {
    key: ?string,
    title?: string,
    description?: string,
    viewChoice: string,
    viewLists?: string,
    adminChoice: string,
    adminLists?: string,
  }
};

const INITIAL_COLLECTION_FORM_STATE = {
  key: null,
  viewChoice: PERM_CHOICE_NONE,
  adminChoice: PERM_CHOICE_NONE
};

export const INITIAL_UI_STATE = {
  collectionForm: INITIAL_COLLECTION_FORM_STATE
};

const updateCollectionForm = (state: CollectionUiState, key: string, newValue: ?string) => ({
  ...state,
  collectionForm: {
    ...state.collectionForm,
    [key]: newValue
  }
});

const reducer = (state: CollectionUiState = INITIAL_UI_STATE, action: Action<any, null>) => {
  switch (action.type) {
  case INIT_COLLECTION_FORM:
    return {
      ...state,
      collectionForm: {
        ...state.collectionForm,
        ...action.payload
      }
    };
  case CLEAR_COLLECTION_FORM:
    return {
      ...state,
      collectionForm: INITIAL_COLLECTION_FORM_STATE
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
  default:
    return state;
  }
};

export default reducer;
