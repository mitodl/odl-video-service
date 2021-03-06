// @flow
import type { Action } from "../flow/reduxTypes"
import { constants } from "../actions/videoUi"
import { CANVASES } from "../constants"
import type { VideoUiState } from "../flow/videoTypes"
import { PERM_CHOICE_COLLECTION, PERM_CHOICE_NONE } from "../lib/dialog"

const {
  INIT_EDIT_VIDEO_FORM,
  SET_EDIT_VIDEO_TITLE,
  SET_EDIT_VIDEO_DESC,
  INIT_UPLOAD_SUBTITLE_FORM,
  SET_UPLOAD_SUBTITLE,
  SET_VIDEOJS_SYNC,
  SET_VIEW_LISTS,
  SET_VIEW_CHOICE,
  SET_VIDEO_FORM_ERRORS,
  SET_PERM_OVERRIDE_CHOICE,
  CLEAR_VIDEO_FORM,
  SET_VIDEO_TIME,
  SET_VIDEO_DURATION,
  TOGGLE_ANALYTICS_OVERLAY,
  SET_SHARE_VIDEO_TIME_ENABLED,
  SET_CURRENT_VIDEO_KEY,
  SET_CURRENT_SUBTITLES_KEY
} = constants

export const INITIAL_EDIT_VIDEO_FORM_STATE = {
  key:            null,
  title:          "",
  description:    "",
  overrideChoice: PERM_CHOICE_COLLECTION,
  viewChoice:     PERM_CHOICE_NONE,
  viewLists:      null
}

export const INITIAL_UPLOAD_SUBTITLE_FORM_STATE = {
  key:      null,
  language: "en",
  subtitle: null
}

export const INITIAL_SHARE_VIDEO_FORM_STATE = {
  shareTime: false,
  videoTime: 0
}

export const INITIAL_UI_STATE = {
  videoTime:                 0,
  duration:                  0,
  editVideoForm:             INITIAL_EDIT_VIDEO_FORM_STATE,
  videoSubtitleForm:         INITIAL_UPLOAD_SUBTITLE_FORM_STATE,
  shareVideoForm:            INITIAL_SHARE_VIDEO_FORM_STATE,
  corner:                    Object.keys(CANVASES)[0],
  analyticsOverlayIsVisible: false,
  currentVideoKey:           null,
  currentSubtitlesKey:       null
}

const updateVideoForm = (
  state: VideoUiState,
  key: string,
  newValue: ?string
) => ({
  ...state,
  editVideoForm: {
    ...state["editVideoForm"],
    [key]: newValue
  }
})

const reducer = (
  state: VideoUiState = INITIAL_UI_STATE,
  action: Action<any, null>
) => {
  switch (action.type) {
  case INIT_EDIT_VIDEO_FORM:
    return {
      ...state,
      editVideoForm: {
        ...state.editVideoForm,
        ...action.payload
      }
    }
  case SET_EDIT_VIDEO_TITLE:
    return updateVideoForm(state, "title", action.payload)
  case SET_EDIT_VIDEO_DESC:
    return updateVideoForm(state, "description", action.payload)
  case SET_PERM_OVERRIDE_CHOICE:
    return updateVideoForm(state, "overrideChoice", action.payload)
  case SET_VIEW_CHOICE:
    return updateVideoForm(state, "viewChoice", action.payload)
  case SET_VIEW_LISTS:
    return updateVideoForm(state, "viewLists", action.payload)
  case INIT_UPLOAD_SUBTITLE_FORM:
    return {
      ...state,
      videoSubtitleForm: {
        ...INITIAL_UPLOAD_SUBTITLE_FORM_STATE,
        ...action.payload
      }
    }
  case SET_UPLOAD_SUBTITLE:
    return {
      ...state,
      videoSubtitleForm: {
        ...state.videoSubtitleForm,
        subtitle: action.payload
      }
    }
  case SET_SHARE_VIDEO_TIME_ENABLED:
    return {
      ...state,
      shareVideoForm: {
        ...state.shareVideoForm,
        shareTime: action.payload
      }
    }
  case SET_VIDEO_TIME:
    return {
      ...state,
      videoTime: action.payload
    }
  case SET_VIDEO_DURATION:
    return {
      ...state,
      duration: action.payload
    }
  case SET_VIDEOJS_SYNC:
    return { ...state, corner: action.payload }
  case SET_VIDEO_FORM_ERRORS:
    return {
      ...state,
      errors: action.payload.errors
    }
  case CLEAR_VIDEO_FORM:
    return {
      ...state,
      editVideoForm:     INITIAL_EDIT_VIDEO_FORM_STATE,
      videoSubtitleForm: INITIAL_UPLOAD_SUBTITLE_FORM_STATE,
      shareVideoForm:    INITIAL_SHARE_VIDEO_FORM_STATE
    }
  case TOGGLE_ANALYTICS_OVERLAY:
    return {
      ...state,
      analyticsOverlayIsVisible: !state.analyticsOverlayIsVisible
    }
  case SET_CURRENT_VIDEO_KEY:
    return {
      ...state,
      currentVideoKey: action.payload.videoKey
    }
  case SET_CURRENT_SUBTITLES_KEY:
    return {
      ...state,
      currentSubtitlesKey: action.payload.subtitlesKey
    }
  default:
    return state
  }
}

export default reducer
