// @flow
import { assert } from "chai"
import configureTestStore from "redux-asserts"

import rootReducer from "../reducers"
import {
  INITIAL_EDIT_VIDEO_FORM_STATE,
  INITIAL_UPLOAD_SUBTITLE_FORM_STATE
} from "./videoUi"
import {
  initEditVideoForm,
  setEditVideoDesc,
  setEditVideoTitle,
  setUploadSubtitle
} from "../actions/videoUi"
import { PERM_CHOICE_NONE } from "../lib/dialog"

describe("videoUi", () => {
  let store

  beforeEach(() => {
    store = configureTestStore(rootReducer)
  })

  it("has some initial state", () => {
    assert.deepEqual(store.getState().videoUi, {
      videoSubtitleForm: INITIAL_UPLOAD_SUBTITLE_FORM_STATE,
      editVideoForm:     INITIAL_EDIT_VIDEO_FORM_STATE,
      corner:            "camera1"
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
})
