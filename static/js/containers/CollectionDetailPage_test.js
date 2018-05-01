// @flow
/* global SETTINGS: false */
import React from "react"
import sinon from "sinon"
import { mount, shallow } from "enzyme"
import { assert } from "chai"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"

import ConnectedCollectionDetailPage from "./CollectionDetailPage"
import {
  CollectionDetailPage as UnconnectedCollectionDetailPage
} from "./CollectionDetailPage"

import * as api from "../lib/api"
import { actions } from "../actions"
import {
  INIT_COLLECTION_FORM,
  SET_IS_NEW,
  SET_SELECTED_VIDEO_KEY
} from "../actions/collectionUi"
import { HIDE_MENU, SHOW_DIALOG, SHOW_MENU } from "../actions/commonUi"
import rootReducer from "../reducers"
import { makeCollection } from "../factories/collection"
import { makeVideos } from "../factories/video"
import { expect } from "../util/test_utils"
import { DIALOGS } from "../constants"
import { makeInitializedForm } from "../lib/collection"
import * as videoUiActions from "../actions/videoUi"
import { PERM_CHOICE_COLLECTION } from "../lib/dialog"

const { INIT_EDIT_VIDEO_FORM } = videoUiActions.constants

describe("CollectionDetailPage", () => {
  let sandbox, store, getCollectionStub, collection, listenForActions
  let actionsToAwait

  const selectors = {
    TITLE:         ".collection-detail-content h1",
    DESCRIPTION:   "p.description",
    MENU_BTN:      ".menu-button",
    SETTINGS_BTN:  "#edit-collection-button",
    DROPBOX_BTN:   ".dropbox-btn",
    NO_VIDEOS_MSG: ".no-videos"
  }

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    collection = makeCollection()
    const collections = [makeCollection(), collection]

    getCollectionStub = sandbox
      .stub(api, "getCollection")
      .returns(Promise.resolve(collection))
    sandbox
      .stub(api, "getCollections")
      .returns(Promise.resolve({ results: collections }))

    actionsToAwait = [
      actions.collections.get.requestType,
      actions.collections.get.successType
    ]
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderPage = async (props = {}) => {
    let wrapper
    // Simulate the react-router match object
    const matchObj = { params: { collectionKey: collection.key } }
    await listenForActions(
      actionsToAwait,
      () => {
        wrapper = mount(
          <Provider store={store}>
            <ConnectedCollectionDetailPage match={matchObj} {...props} />
          </Provider>
        )
      }
    )
    if (!wrapper) throw new Error("Never will happen, make flow happy")
    wrapper.update()
    return wrapper
  }

  it("fetches requirements on load", async () => {
    await renderPage()
    sinon.assert.calledWith(getCollectionStub, collection.key)
  })

  it("renders each video in the collection", async () => {
    const addedVideos = makeVideos(3, collection.key)
    const expectedVideoCount = collection.videos.length + addedVideos.length
    collection.videos = collection.videos.concat(addedVideos)

    const wrapper = await renderPage()
    assert.lengthOf(wrapper.find("VideoCard"), expectedVideoCount)
  })

  it("shows a message when no videos have been added to the collection yet", async () => {
    collection.videos = []
    const wrapper = await renderPage()
    const messageContainer = wrapper.find(selectors.NO_VIDEOS_MSG)
    assert.isTrue(messageContainer.exists())
    assert.include(messageContainer.text(), "You have not added any videos yet")
  })

  describe("when there is an error", () => {
    const error = {
      detail:          "Verboten Badness",
      errorStatusCode: 403
    }

    it("shows an error message", async () => {
      const wrapper = shallow(
        <UnconnectedCollectionDetailPage
          collectionError={error}
        />
      )
      const errorMessageEl = wrapper.find("ErrorMessage")
      assert.deepEqual(
        errorMessageEl.get(0).props.children,
        ["Error: ", error.detail]
      )
    })
  })

  ;[
    ["Collection description", true, "non-empty description"],
    [null, false, "empty description"]
  ].forEach(([collectionDescription, shouldShow, testDescriptor]) => {
    it(`description ${expect(
      shouldShow
    )} be shown with ${testDescriptor}`, async () => {
      collection.description = collectionDescription
      const wrapper = await renderPage()
      const descriptionEl = wrapper.find(selectors.DESCRIPTION)
      assert.equal(descriptionEl.exists(), shouldShow)
      if (shouldShow) {
        assert.equal(descriptionEl.text(), collectionDescription)
      }
    })
  })
  ;[[2, true, "one or more videos"], [0, false, "no videos"]].forEach(
    ([videoCount, shouldShow, testDescriptor]) => {
      it(`video count ${expect(
        shouldShow
      )} be shown with ${testDescriptor}`, async () => {
        collection.videos = makeVideos(videoCount, collection.key)
        const wrapper = await renderPage()
        const titleText = wrapper.find(selectors.TITLE).text()
        assert.equal(titleText.indexOf(`(${videoCount})`) >= 0, shouldShow)
      })
    }
  )

  it("has a toolbar whose handler will dispatch an action to open the drawer", async () => {
    const wrapper = await renderPage()
    wrapper.find(selectors.MENU_BTN).simulate("click")
    assert.isTrue(store.getState().commonUi.drawerOpen)
  })
  ;[
    [false, false, "user without admin permissions"],
    [true, true, "user with admin permissions"]
  ].forEach(([adminPermissionSetting, shouldShow, testDescriptor]) => {
    it(`${expect(
      shouldShow
    )} render VideoCard with admin flag for ${testDescriptor}`, async () => {
      collection.is_admin = adminPermissionSetting
      const wrapper = await renderPage()
      assert.equal(
        wrapper
          .find("VideoCard")
          .first()
          .prop("isAdmin"),
        shouldShow
      )
    })
  })
  ;[
    [false, false, "user without admin permissions"],
    [true, true, "user with admin permissions"]
  ].forEach(([adminPermissionSetting, shouldShow, testDescriptor]) => {
    it(`${expect(
      shouldShow
    )} show dropbox upload & settings buttons for ${testDescriptor}`, async () => {
      collection.is_admin = adminPermissionSetting
      const wrapper = await renderPage()
      assert.equal(wrapper.find(selectors.DROPBOX_BTN).exists(), shouldShow)
      assert.equal(wrapper.find(selectors.SETTINGS_BTN).exists(), shouldShow)
    })
  })

  it("uploads a video and reloads the collection page", async () => {
    const uploadVideoStub = sandbox
      .stub(api, "uploadVideo")
      .returns(Promise.resolve({}))
    const mockFiles = [{ name: "file1" }, { name: "file2" }]
    collection.is_admin = true
    const wrapper = await renderPage()

    await listenForActions(
      [
        actions.uploadVideo.post.requestType,
        actions.uploadVideo.post.successType,
        actions.collections.get.requestType
      ],
      () => {
        wrapper.find("DropboxChooser").prop("success")(mockFiles)
      }
    )

    sinon.assert.calledWith(uploadVideoStub, collection.key, mockFiles)
  })

  it("shows the edit video dialog", async () => {
    const wrapper = await renderPage()
    const state = await listenForActions(
      [SET_SELECTED_VIDEO_KEY, SHOW_DIALOG, INIT_EDIT_VIDEO_FORM],
      () => {
        wrapper
          .find("VideoCard")
          .first()
          .prop("showEditDialog")()
      }
    )

    const video = collection.videos[0]
    assert.equal(state.collectionUi.selectedVideoKey, video.key)
    assert.isTrue(state.commonUi.dialogVisibility[DIALOGS.EDIT_VIDEO])
    assert.deepEqual(state.videoUi.editVideoForm, {
      description:    video.description,
      key:            video.key,
      title:          video.title,
      overrideChoice: PERM_CHOICE_COLLECTION,
      viewChoice:     PERM_CHOICE_COLLECTION,
      viewLists:      ""
    })
  })

  it("shows the share video dialog", async () => {
    const wrapper = await renderPage()
    const state = await listenForActions(
      [SET_SELECTED_VIDEO_KEY, SHOW_DIALOG],
      () => {
        wrapper
          .find("VideoCard")
          .first()
          .prop("showShareDialog")()
      }
    )
    assert.equal(state.collectionUi.selectedVideoKey, collection.videos[0].key)
    assert.isTrue(state.commonUi.dialogVisibility[DIALOGS.SHARE_VIDEO])
  })

  it("clicks the edit collection button", async () => {
    const wrapper = await renderPage()
    const eventStub = {
      preventDefault: sandbox.stub()
    }
    const state = await listenForActions(
      [INIT_COLLECTION_FORM, SET_IS_NEW, SHOW_DIALOG],
      () => {
        wrapper.find("#edit-collection-button").prop("onClick")(eventStub)
      }
    )
    sinon.assert.calledWith(eventStub.preventDefault)
    assert.isFalse(state.collectionUi.isNew)
    assert.deepEqual(
      state.collectionUi.editCollectionForm,
      makeInitializedForm(collection)
    )
    assert.isTrue(state.commonUi.dialogVisibility[DIALOGS.COLLECTION_FORM])
  })
  ;[
    ["showVideoMenu", true, [SET_SELECTED_VIDEO_KEY, SHOW_MENU]],
    ["closeVideoMenu", false, [SET_SELECTED_VIDEO_KEY, HIDE_MENU]]
  ].forEach(([action, expectedVisibility, expectedActions]) => {
    it(`${action} sets menu visibility to ${expectedVisibility.toString()}`, async () => {
      const wrapper = await renderPage()
      const state = await listenForActions(expectedActions, () => {
        wrapper
          .find("VideoCard")
          .first()
          .prop(action)()
      })
      const video = collection.videos[0]
      assert.equal(state.commonUi.menuVisibility[video.key], expectedVisibility)
    })
  })
})
