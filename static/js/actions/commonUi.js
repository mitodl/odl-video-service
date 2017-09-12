// @flow
import { createAction } from 'redux-actions';

export const qualifiedName = (name: string) => `UI_${name}`;

export const SET_DRAWER_OPEN = qualifiedName('SET_DRAWER_OPEN');
export const setDrawerOpen = createAction(SET_DRAWER_OPEN);

export const SHOW_DIALOG = qualifiedName('SHOW_DIALOG');
export const showDialog = createAction(SHOW_DIALOG);

export const HIDE_DIALOG = qualifiedName('HIDE_DIALOG');
export const hideDialog = createAction(HIDE_DIALOG);

export const INIT_EDIT_VIDEO_FORM = qualifiedName('INIT_EDIT_VIDEO_FORM');
export const initEditVideoForm = createAction(INIT_EDIT_VIDEO_FORM);

export const SET_EDIT_VIDEO_TITLE = qualifiedName('SET_EDIT_VIDEO_TITLE');
export const setEditVideoTitle = createAction(SET_EDIT_VIDEO_TITLE);

export const SET_EDIT_VIDEO_DESC = qualifiedName('SET_EDIT_VIDEO_DESC');
export const setEditVideoDesc = createAction(SET_EDIT_VIDEO_DESC);
