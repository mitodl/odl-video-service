// @flow
import { createAction } from 'redux-actions';

export const qualifiedName = (name: string) => `UI_${name}`;

export const SET_DRAWER_OPEN = qualifiedName('SET_DRAWER_OPEN');
export const setDrawerOpen = createAction(SET_DRAWER_OPEN);

export const SHOW_DIALOG = qualifiedName('SHOW_DIALOG');
export const showDialog = createAction(SHOW_DIALOG);

export const HIDE_DIALOG = qualifiedName('HIDE_DIALOG');
export const hideDialog = createAction(HIDE_DIALOG);
