// @flow
import { createAction } from "redux-actions"

export const qualifiedName = (name: string) => `VIDEO_UI_${name}`
const constants = {}
const actionCreators = {}

constants.INIT_EDIT_VIDEO_FORM = qualifiedName("INIT_EDIT_VIDEO_FORM")
actionCreators.initEditVideoForm = createAction(constants.INIT_EDIT_VIDEO_FORM)

constants.SET_EDIT_VIDEO_TITLE = qualifiedName("SET_EDIT_VIDEO_TITLE")
actionCreators.setEditVideoTitle = createAction(constants.SET_EDIT_VIDEO_TITLE)

constants.SET_EDIT_VIDEO_DESC = qualifiedName("SET_EDIT_VIDEO_DESC")
actionCreators.setEditVideoDesc = createAction(constants.SET_EDIT_VIDEO_DESC)

constants.SET_UPLOAD_SUBTITLE = qualifiedName("SET_UPLOAD_SUBTITLE")
actionCreators.setUploadSubtitle = createAction(constants.SET_UPLOAD_SUBTITLE)

constants.INIT_UPLOAD_SUBTITLE_FORM = qualifiedName("INIT_UPLOAD_SUBTITLE_FORM")

constants.SET_VIDEOJS_SYNC = qualifiedName("SET_VIDEOJS_SYNC")
actionCreators.updateVideoJsSync = createAction(constants.SET_VIDEOJS_SYNC)

constants.SET_PERM_OVERRIDE_CHOICE = qualifiedName("SET_PERM_OVERRIDE_CHOICE")
actionCreators.setPermOverrideChoice = createAction(
  constants.SET_PERM_OVERRIDE_CHOICE
)

constants.SET_VIEW_CHOICE = qualifiedName("SET_VIEW_CHOICE")
actionCreators.setViewChoice = createAction(constants.SET_VIEW_CHOICE)

constants.SET_VIEW_LISTS = qualifiedName("SET_VIEW_LISTS")
actionCreators.setViewLists = createAction(constants.SET_VIEW_LISTS)

constants.SET_VIDEO_FORM_ERRORS = qualifiedName("SET_VIDEO_FORM_ERRORS")
actionCreators.setVideoFormErrors = createAction(
  constants.SET_VIDEO_FORM_ERRORS
)

constants.CLEAR_VIDEO_FORM = qualifiedName("CLEAR_VIDEO_FORM")
actionCreators.clearVideoForm = createAction(constants.CLEAR_VIDEO_FORM)

constants.SET_VIDEO_TIME = qualifiedName("SET_VIDEO_TIME")
actionCreators.setVideoTime = createAction(constants.SET_VIDEO_TIME)

constants.SET_VIDEO_DURATION = qualifiedName("SET_VIDEO_DURATION")
actionCreators.setVideoDuration = createAction(constants.SET_VIDEO_DURATION)

constants.TOGGLE_ANALYTICS_OVERLAY = qualifiedName("TOGGLE_ANALYTICS_OVERLAY")
actionCreators.toggleAnalyticsOverlay = createAction(
  constants.TOGGLE_ANALYTICS_OVERLAY
)

constants.SET_SHARE_VIDEO_TIME_ENABLED = qualifiedName(
  "SET_SHARE_VIDEO_TIME_ENABLED"
)
actionCreators.setShareVideoTimeEnabled = createAction(
  constants.SET_SHARE_VIDEO_TIME_ENABLED
)

constants.SET_CURRENT_VIDEO_KEY = qualifiedName("SET_CURRENT_VIDEO_KEY")
actionCreators.setCurrentVideoKey = createAction(
  constants.SET_CURRENT_VIDEO_KEY)

constants.SET_CURRENT_SUBTITLES_KEY = qualifiedName("SET_CURRENT_SUBTITLES_KEY")
actionCreators.setCurrentSubtitlesKey = createAction(
  constants.SET_CURRENT_SUBTITLES_KEY)

export { actionCreators, constants }
