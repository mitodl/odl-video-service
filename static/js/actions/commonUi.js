// @flow
import { createAction } from 'redux-actions';

export const qualifiedName = (name: string) => `COMMON_UI_${name}`;

export const SET_DRAWER_OPEN = qualifiedName('SET_DRAWER_OPEN');
export const setDrawerOpen = createAction(SET_DRAWER_OPEN);

