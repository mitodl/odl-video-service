// @flow
import { createAction } from 'redux-actions';

export const qualifiedName = (name: string) => `VIDEO_UI_${name}`;

export const INIT_EDIT_VIDEO_FORM = qualifiedName('INIT_EDIT_VIDEO_FORM');
export const initEditVideoForm = createAction(INIT_EDIT_VIDEO_FORM);

export const SET_EDIT_VIDEO_TITLE = qualifiedName('SET_EDIT_VIDEO_TITLE');
export const setEditVideoTitle = createAction(SET_EDIT_VIDEO_TITLE);

export const SET_EDIT_VIDEO_DESC = qualifiedName('SET_EDIT_VIDEO_DESC');
export const setEditVideoDesc = createAction(SET_EDIT_VIDEO_DESC);

export const SET_UPLOAD_SUBTITLE = qualifiedName('SET_UPLOAD_SUBTITLE');
export const setUploadSubtitle = createAction(SET_UPLOAD_SUBTITLE);

export const INIT_UPLOAD_SUBTITLE_FORM = qualifiedName('INIT_UPLOAD_SUBTITLE_FORM');

export const SET_VIDEOJS_SYNC = qualifiedName('SET_VIDEOJS_SYNC');
export const updateVideoJsSync = createAction(SET_VIDEOJS_SYNC);

export const SET_PERM_OVERRIDE_CHOICE = qualifiedName('SET_PERM_OVERRIDE_CHOICE');
export const setPermOverrideChoice = createAction(SET_PERM_OVERRIDE_CHOICE);

export const SET_VIEW_CHOICE = qualifiedName('SET_VIEW_CHOICE');
export const setViewChoice = createAction(SET_VIEW_CHOICE);

export const SET_VIEW_LISTS = qualifiedName('SET_VIEW_LISTS');
export const setViewLists = createAction(SET_VIEW_LISTS);

export const SET_VIDEO_FORM_ERRORS = qualifiedName('SET_VIDEO_FORM_ERRORS');
export const setVideoFormErrors = createAction(SET_VIDEO_FORM_ERRORS);

export const CLEAR_VIDEO_FORM = qualifiedName('CLEAR_VIDEO_FORM');
export const clearVideoForm = createAction(CLEAR_VIDEO_FORM);
