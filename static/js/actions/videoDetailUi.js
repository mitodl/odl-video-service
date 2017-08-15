// @flow
import { createAction } from 'redux-actions';

export const qualifiedName = (name: string) => `VIDEO_DETAIL_UI_${name}`;

export const SET_DIALOG_VISIBILITY = qualifiedName('SET_DIALOG_VISIBILITY');
export const setDialogVisibility = createAction(SET_DIALOG_VISIBILITY);

export const SET_DRAWER_OPEN = qualifiedName('SET_DRAWER_OPEN');
export const setDrawerOpen = createAction(SET_DRAWER_OPEN);

export const SET_TITLE = qualifiedName('SET_TITLE');
export const setTitle = createAction(SET_TITLE);

export const SET_DESCRIPTION = qualifiedName('SET_DESCRIPTION');
export const setDescription = createAction(SET_DESCRIPTION);

export const CLEAR_DIALOG = qualifiedName('CLEAR_DIALOG');
export const clearDialog = createAction(CLEAR_DIALOG);
