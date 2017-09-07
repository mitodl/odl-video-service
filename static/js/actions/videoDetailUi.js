// @flow
import { createAction } from 'redux-actions';

export const qualifiedName = (name: string) => `VIDEO_DETAIL_UI_${name}`;

export const SET_EDIT_DIALOG_VISIBILITY = qualifiedName('SET_EDIT_DIALOG_VISIBILITY');
export const setEditDialogVisibility = createAction(SET_EDIT_DIALOG_VISIBILITY);

export const SET_TITLE = qualifiedName('SET_TITLE');
export const setTitle = createAction(SET_TITLE);

export const SET_DESCRIPTION = qualifiedName('SET_DESCRIPTION');
export const setDescription = createAction(SET_DESCRIPTION);

export const CLEAR_EDIT_DIALOG = qualifiedName('CLEAR_EDIT_DIALOG');
export const clearEditDialog = createAction(CLEAR_EDIT_DIALOG);

export const SET_SHARE_DIALOG_VISIBILITY = qualifiedName('SET_SHARE_DIALOG_VISIBILITY');
export const setShareDialogVisibility = createAction(SET_SHARE_DIALOG_VISIBILITY);

export const CLEAR_SHARE_DIALOG = qualifiedName('CLEAR_SHARE_DIALOG');
export const clearShareDialog = createAction(CLEAR_SHARE_DIALOG);
