// @flow
import { createAction } from 'redux-actions';

export const qualifiedName = (name: string) => `COLLECTION_UI_${name}`;

export const INIT_COLLECTION_FORM = qualifiedName('INIT_COLLECTION_FORM');
export const initCollectionForm = createAction(INIT_COLLECTION_FORM);

export const CLEAR_COLLECTION_FORM = qualifiedName('CLEAR_COLLECTION_FORM');
export const clearCollectionForm = createAction(CLEAR_COLLECTION_FORM);

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
