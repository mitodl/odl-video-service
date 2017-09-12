// @flow
import { createAction } from 'redux-actions';

export const qualifiedName = (name: string) => `VIDEO_DETAIL_UI_${name}`;

export const SET_SHARE_DIALOG_VISIBILITY = qualifiedName('SET_SHARE_DIALOG_VISIBILITY');
export const setShareDialogVisibility = createAction(SET_SHARE_DIALOG_VISIBILITY);

export const CLEAR_SHARE_DIALOG = qualifiedName('CLEAR_SHARE_DIALOG');
export const clearShareDialog = createAction(CLEAR_SHARE_DIALOG);
