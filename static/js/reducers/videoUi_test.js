// @flow
import { assert } from "chai"
import configureTestStore from "redux-asserts"

import rootReducer from "../reducers"
import {
  INITIAL_UI_STATE,
  INITIAL_EDIT_VIDEO_FORM_STATE,
  INITIAL_SHARE_VIDEO_FORM_STATE,
  INITIAL_UPLOAD_SUBTITLE_FORM_STATE
} from "./videoUi"
import { actionCreators } from "../actions/videoUi"
const {
  clearVideoForm,
  initEditVideoForm,
  setEditVideoDesc,
  setEditVideoTitle,
  setUploadSubtitle,
  setVideoTime,
  setVideoDuration,
  toggleAnalyticsOverlay
} = actionCreators
import { PERM_CHOICE_NONE } from "../lib/dialog"

describe("videoUi", () => {
  let store

  beforeEach(() => {
    store = configureTestStore(rootReducer)
  })

  it("has some initial state", () => {
    assert.deepEqual(store.getState().videoUi, {
      videoSubtitleForm:         INITIAL_UPLOAD_SUBTITLE_FORM_STATE,
      editVideoForm:             INITIAL_EDIT_VIDEO_FORM_STATE,
      shareVideoForm:            INITIAL_SHARE_VIDEO_FORM_STATE,
      corner:                    "camera1",
      duration:                  0,
      videoTime:                 0,
      analyticsOverlayIsVisible: false
    })
  })

  it("has action that sets the file to upload", () => {
    assert.deepEqual(
      store.getState().videoUi.videoSubtitleForm,
      INITIAL_UPLOAD_SUBTITLE_FORM_STATE
    )
    const fileUpload = { name: "foo.vtt", data: "ddd" }
    store.dispatch(setUploadSubtitle(fileUpload))
    assert.equal(
      store.getState().videoUi.videoSubtitleForm.subtitle,
      fileUpload
    )
  })

  it("has actions that set video title and description", () => {
    assert.deepEqual(
      store.getState().videoUi.editVideoForm,
      INITIAL_EDIT_VIDEO_FORM_STATE
    )
    store.dispatch(setEditVideoTitle("title"))
    store.dispatch(setEditVideoDesc("description"))
    assert.equal(store.getState().videoUi.editVideoForm.title, "title")
    assert.equal(
      store.getState().videoUi.editVideoForm.description,
      "description"
    )
  })

  it("has an action that initializes the edit video form,", () => {
    const formObj = {
      key:            "key",
      title:          "title",
      description:    "description",
      viewChoice:     PERM_CHOICE_NONE,
      viewLists:      [],
      overrideChoice: "collection"
    }
    store.dispatch(initEditVideoForm(formObj))
    assert.deepEqual(store.getState().videoUi.editVideoForm, formObj)
  })

  it("has an action that sets the video time,", () => {
    const videoTime = 42
    assert.notEqual(store.getState().videoUi.videoTime, videoTime)
    store.dispatch(setVideoTime(42))
    assert.equal(store.getState().videoUi.videoTime, videoTime)
  })

  it("has an action that sets the duration,", () => {
    const duration = 42
    assert.notEqual(store.getState().videoUi.duration, duration)
    store.dispatch(setVideoDuration(42))
    assert.equal(store.getState().videoUi.duration, duration)
  })

  it("has an action that toggles analytics overlay", () => {
    const _selectValue = () => store.getState().videoUi.analyticsOverlayIsVisible
    assert.equal(_selectValue(), false)
    store.dispatch(toggleAnalyticsOverlay())
    assert.equal(_selectValue(), true)
    store.dispatch(toggleAnalyticsOverlay())
    assert.equal(_selectValue(), false)
  })

  describe("CLEAR_VIDEO_FORM", () => {
    const initialVideoUiState = {
      ...INITIAL_UI_STATE,
      videoTime:                 42,
      duration:                  42,
      analyticsOverlayIsVisible: true,
      corner:                    42,
      editVideoForm:             {
        ...INITIAL_EDIT_VIDEO_FORM_STATE,
        key: 'someKey',
      },
      videoSubtitleForm: {
        ...INITIAL_UPLOAD_SUBTITLE_FORM_STATE,
        key: 'someOtherKey',
      },
      shareVideoForm: {
        ...INITIAL_SHARE_VIDEO_FORM_STATE,
        shareTime: 42,
      },
    }

    beforeEach(() => {
      // $FlowFixMe : flow thinks 2nd parameter is not used, but it is.
      store = configureTestStore(rootReducer, {videoUi: initialVideoUiState})
    })

    it("clears forms but preserves other state values", () => {
      const _selectState = () => store.getState().videoUi
      assert.equal(_selectState(), initialVideoUiState)
      store.dispatch(clearVideoForm())
      assert.deepEqual(_selectState(), {
        ...initialVideoUiState,
        editVideoForm:     INITIAL_EDIT_VIDEO_FORM_STATE,
        videoSubtitleForm: INITIAL_UPLOAD_SUBTITLE_FORM_STATE,
        shareVideoForm:    INITIAL_SHARE_VIDEO_FORM_STATE,
      })
    })
  })
})
