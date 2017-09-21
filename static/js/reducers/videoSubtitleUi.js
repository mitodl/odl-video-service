// @flow
import type { Action } from "../flow/reduxTypes";
import {
  INIT_UPLOAD_SUBTITLE_FORM,
  SET_UPLOAD_SUBTITLE,
} from "../actions/videoSubtitleUi";

export type SubtitleUiState = {
  videoSubtitleForm: {
    key: ?string,
    language: string,
    subtitle: ?File
  }
};

export const INITIAL_UPLOAD_SUBTITLE_FORM_STATE = {
  key: null,
  language: "en",
  subtitle: null
};

export const INITIAL_UI_STATE = {
  videoSubtitleForm: INITIAL_UPLOAD_SUBTITLE_FORM_STATE
};

const reducer = (state: SubtitleUiState = INITIAL_UI_STATE, action: Action<any, null>) => {
  switch (action.type) {
  case INIT_UPLOAD_SUBTITLE_FORM:
    return {
      ...state,
      videoSubtitleForm: {
        ...INITIAL_UPLOAD_SUBTITLE_FORM_STATE,
        ...action.payload
      }
    };
  case SET_UPLOAD_SUBTITLE:
    return {...state, videoSubtitleForm: { ...state.videoSubtitleForm, subtitle: action.payload }};
  default:
    return state;
  }
};

export default reducer;
