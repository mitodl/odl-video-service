// @flow
import { createAction } from 'redux-actions';

export const qualifiedName = (name: string) => `VIDEO_UI_${name}`;

export const SET_UPLOAD_SUBTITLE = qualifiedName('SET_UPLOAD_SUBTITLE');
export const setUploadSubtitle = createAction(SET_UPLOAD_SUBTITLE);

export const INIT_UPLOAD_SUBTITLE_FORM = qualifiedName('INIT_UPLOAD_SUBTITLE_FORM');

export const SET_VIDEOJS_SYNC = qualifiedName('SET_VIDEOJS_SYNC');
export const updateVideoJsSync = createAction(SET_VIDEOJS_SYNC);
