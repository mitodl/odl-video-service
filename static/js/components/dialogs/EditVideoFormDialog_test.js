// @flow
/* global SETTINGS: false */
import React from "react"
import sinon from "sinon"
import { mount } from "enzyme"
import { assert } from "chai"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"
import _ from "lodash"

import EditVideoFormDialog from "./EditVideoFormDialog"

import rootReducer from "../../reducers"
import { actions } from "../../actions"
import {
  INIT_EDIT_VIDEO_FORM,
  initEditVideoForm,
  setEditVideoTitle,
  setEditVideoDesc,
  setViewLists,
  setViewChoice,
  setPermOverrideChoice,
  SET_EDIT_VIDEO_TITLE,
  SET_EDIT_VIDEO_DESC,
  SET_VIEW_CHOICE,
  SET_VIEW_LISTS,
  SET_PERM_OVERRIDE_CHOICE,
  SET_VIDEO_FORM_ERRORS
} from "../../actions/videoUi"
import { setSelectedVideoKey } from "../../actions/collectionUi"
import { INITIAL_UI_STATE } from "../../reducers/videoUi"
import * as api from "../../lib/api"
import { makeVideo, makeVideoSubtitle } from "../../factories/video"
import { makeCollection } from "../../factories/collection"
import { expect } from "../../util/test_utils"
import {
  PERM_CHOICE_LISTS,
  PERM_CHOICE_NONE,
  PERM_CHOICE_OVERRIDE,
  PERM_CHOICE_PUBLIC
} from "../../lib/dialog"

describe("EditVideoFormDialog", () => {
  let sandbox, store, listenForActions, hideDialogStub, video
  const selectors = {
    SUBMIT_BTN:  "button.mdc-dialog__footer__button--accept",
    TITLE_INPUT: "#video-title",
    DESC_INPUT:  "#video-description"
  }

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    hideDialogStub = sandbox.stub()
    video = makeVideo()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (props = {}) => {
    return mount(
      <Provider store={store}>
        <div>
          <EditVideoFormDialog
            open={true}
            hideDialog={hideDialogStub}
            video={video}
            videoUi={INITIAL_UI_STATE}
            {...props}
          />
        </div>
      </Provider>
    )
  }

  it("initializes the form when given a video that doesn't match the current form key", async () => {
    let wrapper
    store.dispatch(initEditVideoForm({ key: "mismatching-key" }))
    const previousFormState = store.getState().videoUi.editVideoForm
    await listenForActions([INIT_EDIT_VIDEO_FORM], () => {
      wrapper = renderComponent()
    })
    if (!wrapper) throw new Error("Render failed")

    assert.notEqual(
      previousFormState.key,
      store.getState().videoUi.editVideoForm.key
    )
    assert.equal(
      wrapper.find(selectors.TITLE_INPUT).hostNodes().prop("value"),
      video.title
    )
    assert.equal(
      wrapper.find(selectors.DESC_INPUT).hostNodes().prop("value"),
      video.description
    )
  })

  it("doesn't re-initialize the form when given a video that matches the current form key", () => {
    store.dispatch(initEditVideoForm({ key: video.key }))
    const previousFormState = store.getState().videoUi.editVideoForm
    renderComponent()
    assert.deepEqual(previousFormState, store.getState().videoUi.editVideoForm)
  })

  for (const [selector, prop, actionType, newValue] of [
    ["#video-title", "title", SET_EDIT_VIDEO_TITLE, "new title"],
    [
      "#video-description",
      "description",
      SET_EDIT_VIDEO_DESC,
      "new description"
    ],
    ["#view-moira-input", "viewLists", SET_VIEW_LISTS, "a,b,c"],
    [
      "#video-view-perms-override-view-collection-override",
      "overrideChoice",
      SET_PERM_OVERRIDE_CHOICE,
      PERM_CHOICE_OVERRIDE
    ],
    [
      "#video-view-perms-view-public",
      "viewChoice",
      SET_VIEW_CHOICE,
      PERM_CHOICE_PUBLIC
    ],
    [
      "#video-view-perms-view-only-me",
      "viewChoice",
      SET_VIEW_CHOICE,
      PERM_CHOICE_NONE
    ]
  ]) {
    it(`sets ${prop}`, async () => {
      SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS = true
      const wrapper = await renderComponent()
      const state = await listenForActions([actionType], () => {
        wrapper.find(selector).hostNodes().simulate("change", {
          target: {
            value: newValue
          }
        })
      })
      assert.equal(state.videoUi.editVideoForm[prop], newValue)
    })
  }

  for (const selector of [
    "#view-moira-input",
    "#video-view-perms-override-view-collection-override",
    "#video-view-perms-view-public",
    "#video-view-perms-view-only-me"
  ]) {
    it(`permissions field ${selector} not present if feature is disabled`, async () => {
      SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS = false
      const wrapper = await renderComponent()
      assert.equal(wrapper.find(selector).hostNodes().length, 0)
    })
  }

  for (const [disabled, count] of [[true, 0], [false, 1]]) {
    it(`public option ${expect(
      disabled
    )} be disabled because subtitle count is ${count}`, async () => {
      SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS = true
      video.is_private = true
      video.videosubtitle_set = []
      if (count === 1) {
        video.videosubtitle_set.push(makeVideoSubtitle(video.key, "fr"))
      }
      const wrapper = await renderComponent()
      const publicOption = wrapper.find("#video-view-perms-view-public").hostNodes().props()
      assert.equal(publicOption.disabled, disabled)
    })
  }

  it(`updates the video when form is submitted and video permissions are disabled`, async () => {
    SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS = false
    let wrapper
    const updateVideoStub = sandbox
      .stub(api, "updateVideo")
      .returns(Promise.resolve(video))
    await listenForActions([INIT_EDIT_VIDEO_FORM], () => {
      wrapper = renderComponent()
    })
    if (!wrapper) throw new Error("Render failed")
    // set title and description, check the values that updateVideoStub is called with
    const newValues = {
      title:       "New Title",
      description: "New Description"
    }
    store.dispatch(setEditVideoTitle(newValues.title))
    store.dispatch(setEditVideoDesc(newValues.description))
    await listenForActions([actions.videos.patch.requestType], () => {
      // Calling onAccept directly b/c click doesn't work in JS tests due to MDC
      // $FlowFixMe: Flow... come on. 'wrapper' cannot be undefined at this point.
      wrapper
        .find("EditVideoFormDialog")
        .find("Dialog")
        .prop("onAccept")()
    })

    sinon.assert.calledWith(updateVideoStub, video.key, newValues)
  })

  it(`updates the video when form is submitted and video permissions are enabled`, async () => {
    SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS = true
    let wrapper
    const updateVideoStub = sandbox
      .stub(api, "updateVideo")
      .returns(Promise.resolve(video))
    await listenForActions([INIT_EDIT_VIDEO_FORM], () => {
      wrapper = renderComponent()
    })
    if (!wrapper) throw new Error("Render failed")
    // set permission override & view choices, check the values that updateVideoStub is called with
    const newValues = {
      title:       "New Title",
      description: "New Description",
      is_private:  false,
      is_public:   false,
      view_lists:  ["my-moira-list1", "my-moira-list2"]
    }
    store.dispatch(setEditVideoTitle(newValues.title))
    store.dispatch(setEditVideoDesc(newValues.description))
    store.dispatch(setPermOverrideChoice(PERM_CHOICE_OVERRIDE))
    store.dispatch(setViewChoice(PERM_CHOICE_LISTS))
    store.dispatch(setViewLists(_.map(newValues.view_lists).join(",")))

    await listenForActions([actions.videos.patch.requestType], () => {
      // Calling onAccept directly b/c click doesn't work in JS tests due to MDC
      // $FlowFixMe: Flow... come on. 'wrapper' cannot be undefined at this point.
      wrapper
        .find("EditVideoFormDialog")
        .find("Dialog")
        .prop("onAccept")()
    })

    sinon.assert.calledWith(updateVideoStub, video.key, newValues)
  })

  it("stores form submission errors in state", async () => {
    const wrapper = await renderComponent()
    const expectedError = "Error: only absolute urls are supported"
    const expectedActionTypes = [
      actions.videos.patch.requestType,
      "RECEIVE_PATCH_VIDEOS_FAILURE",
      SET_VIDEO_FORM_ERRORS
    ]
    await listenForActions(expectedActionTypes, () => {
      // Calling click handler directly due to MDC limitations (can't use enzyme's 'simulate')
      wrapper.find("Dialog").prop("onAccept")()
    })
    assert.equal(store.getState().videoUi.errors, expectedError)
  })

  it("can get a video from the collection state when no video is provided to the component directly", () => {
    const collection = makeCollection()
    const collectionVideo = collection.videos[0]
    store.dispatch(setSelectedVideoKey(collectionVideo.key))
    const wrapper = renderComponent({
      video:      null,
      collection: collection
    })
    const dialogProps = wrapper.find("EditVideoFormDialog").props()
    assert.deepEqual(dialogProps.video, collectionVideo)
    assert.equal(dialogProps.shouldUpdateCollection, true)
  })

  it("prefers a video provided via props over a video in a collection", () => {
    const collection = makeCollection()
    const wrapper = renderComponent({
      video:      video,
      collection: collection
    })
    const dialogProps = wrapper.find("EditVideoFormDialog").props()
    assert.deepEqual(dialogProps.video, video)
    assert.equal(dialogProps.shouldUpdateCollection, false)
  })
})
