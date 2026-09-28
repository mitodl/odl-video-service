import { createAction } from "redux-actions"

export const qualifiedName = (name: string) => `VIDEO_UI_${name}`
/*
 * Object literals rather than assignment onto `{}`. The mutation style only
 * typechecked under Flow because nothing was reading these files; TypeScript
 * infers `{}` and rejects every subsequent property. Literals also mean each
 * `constants.FOO` is checked at its call sites instead of resolving to `any`.
 */
export const constants = {
  INIT_EDIT_VIDEO_FORM:         qualifiedName("INIT_EDIT_VIDEO_FORM"),
  SET_EDIT_VIDEO_TITLE:         qualifiedName("SET_EDIT_VIDEO_TITLE"),
  SET_EDIT_VIDEO_DESC:          qualifiedName("SET_EDIT_VIDEO_DESC"),
  SET_EDIT_VIDEO_DESC_FORMAT:   qualifiedName("SET_EDIT_VIDEO_DESC_FORMAT"),
  SET_EDIT_VIDEO_CTA_LINK:      qualifiedName("SET_EDIT_VIDEO_CTA_LINK"),
  SET_UPLOAD_SUBTITLE:          qualifiedName("SET_UPLOAD_SUBTITLE"),
  INIT_UPLOAD_SUBTITLE_FORM:    qualifiedName("INIT_UPLOAD_SUBTITLE_FORM"),
  SET_VIDEOJS_SYNC:             qualifiedName("SET_VIDEOJS_SYNC"),
  SET_PERM_OVERRIDE_CHOICE:     qualifiedName("SET_PERM_OVERRIDE_CHOICE"),
  SET_VIEW_CHOICE:              qualifiedName("SET_VIEW_CHOICE"),
  SET_VIEW_LISTS:               qualifiedName("SET_VIEW_LISTS"),
  SET_VIDEO_FORM_ERRORS:        qualifiedName("SET_VIDEO_FORM_ERRORS"),
  CLEAR_VIDEO_FORM:             qualifiedName("CLEAR_VIDEO_FORM"),
  SET_VIDEO_TIME:               qualifiedName("SET_VIDEO_TIME"),
  SET_VIDEO_DURATION:           qualifiedName("SET_VIDEO_DURATION"),
  TOGGLE_ANALYTICS_OVERLAY:     qualifiedName("TOGGLE_ANALYTICS_OVERLAY"),
  SET_SHARE_VIDEO_TIME_ENABLED: qualifiedName("SET_SHARE_VIDEO_TIME_ENABLED"),
  SET_CURRENT_VIDEO_KEY:        qualifiedName("SET_CURRENT_VIDEO_KEY"),
  SET_CURRENT_SUBTITLES_KEY:    qualifiedName("SET_CURRENT_SUBTITLES_KEY")
}

export const actionCreators = {
  initEditVideoForm:        createAction(constants.INIT_EDIT_VIDEO_FORM),
  setEditVideoTitle:        createAction(constants.SET_EDIT_VIDEO_TITLE),
  setEditVideoDesc:         createAction(constants.SET_EDIT_VIDEO_DESC),
  setEditVideoDescFormat:   createAction(constants.SET_EDIT_VIDEO_DESC_FORMAT),
  setEditVideoCtaLink:      createAction(constants.SET_EDIT_VIDEO_CTA_LINK),
  setUploadSubtitle:        createAction(constants.SET_UPLOAD_SUBTITLE),
  updateVideoJsSync:        createAction(constants.SET_VIDEOJS_SYNC),
  setPermOverrideChoice:    createAction(constants.SET_PERM_OVERRIDE_CHOICE),
  setViewChoice:            createAction(constants.SET_VIEW_CHOICE),
  setViewLists:             createAction(constants.SET_VIEW_LISTS),
  setVideoFormErrors:       createAction(constants.SET_VIDEO_FORM_ERRORS),
  clearVideoForm:           createAction(constants.CLEAR_VIDEO_FORM),
  setVideoTime:             createAction(constants.SET_VIDEO_TIME),
  setVideoDuration:         createAction(constants.SET_VIDEO_DURATION),
  toggleAnalyticsOverlay:   createAction(constants.TOGGLE_ANALYTICS_OVERLAY),
  setShareVideoTimeEnabled: createAction(
    constants.SET_SHARE_VIDEO_TIME_ENABLED
  ),
  setCurrentVideoKey:     createAction(constants.SET_CURRENT_VIDEO_KEY),
  setCurrentSubtitlesKey: createAction(constants.SET_CURRENT_SUBTITLES_KEY)
}
