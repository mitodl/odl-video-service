// @flow
import { createAction } from 'redux-actions';
import type { Dispatch } from 'redux';

import type { Collection } from "../flow/collectionTypes";
import { showDialog } from './commonUi';
import { DIALOGS } from "../constants";
import { makeInitializedForm } from "../lib/collection";

export const qualifiedName = (name: string) => `COLLECTION_UI_${name}`;

export const INIT_COLLECTION_FORM = qualifiedName('INIT_COLLECTION_FORM');
export const initCollectionForm = createAction(INIT_COLLECTION_FORM);

export const SET_COLLECTION_TITLE = qualifiedName('SET_COLLECTION_TITLE');
export const setCollectionTitle = createAction(SET_COLLECTION_TITLE);

export const SET_COLLECTION_DESC = qualifiedName('SET_COLLECTION_DESC');
export const setCollectionDesc = createAction(SET_COLLECTION_DESC);

export const SET_VIEW_CHOICE = qualifiedName('SET_VIEW_CHOICE');
export const setViewChoice = createAction(SET_VIEW_CHOICE);

export const SET_VIEW_LISTS = qualifiedName('SET_VIEW_LISTS');
export const setViewLists = createAction(SET_VIEW_LISTS);

export const SET_ADMIN_CHOICE = qualifiedName('SET_ADMIN_CHOICE');
export const setAdminChoice = createAction(SET_ADMIN_CHOICE);

export const SET_ADMIN_LISTS = qualifiedName('SET_ADMIN_LISTS');
export const setAdminLists = createAction(SET_ADMIN_LISTS);

export const SET_SELECTED_VIDEO_KEY = qualifiedName('SET_SELECTED_VIDEO_KEY');
export const setSelectedVideoKey = createAction(SET_SELECTED_VIDEO_KEY);

export const SET_IS_NEW = qualifiedName('SET_IS_NEW');
export const setIsNew = createAction(SET_IS_NEW);

export const CLEAR_COLLECTION_FORM = qualifiedName('CLEAR_COLLECTION_FORM');
export const clearCollectionForm = createAction(CLEAR_COLLECTION_FORM);

export const showNewCollectionDialog = () =>
  (dispatch: Dispatch) => {
    dispatch(setIsNew(true));
    dispatch(showDialog(DIALOGS.COLLECTION_FORM));
  };

export const showEditCollectionDialog = (collection: Collection) =>
  (dispatch: Dispatch) => {
    dispatch(setIsNew(false));
    dispatch(initCollectionForm(makeInitializedForm(collection)));
    dispatch(showDialog(DIALOGS.COLLECTION_FORM));
  };

export const SET_COLLECTION_FORM_ERRORS = qualifiedName('SET_COLLECTION_FORM_ERRORS');
export const setCollectionFormErrors = createAction(SET_COLLECTION_FORM_ERRORS);
