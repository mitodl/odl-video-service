// @flow
import React from "react"
import sinon from "sinon"
import moment from "moment"
import { mount } from "enzyme"
import { assert } from "chai"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"

import VideoDetailPage from "./VideoDetailPage"

import * as api from "../lib/api"
import { actions } from "../actions"
import rootReducer from "../reducers"
import { wait } from "../util/util"
import * as libVideo from "../lib/video"
import { makeVideo } from "../factories/video"
import { makeCollectionUrl } from "../lib/urls"
import {
  MM_DD_YYYY,
  VIDEO_STATUS_TRANSCODING,
  VIDEO_STATUS_ERROR
} from "../constants"

import type { Video } from "../flow/videoTypes"

describe("VideoDetailPage", () => {
  let sandbox, store, getVideoStub, dropboxStub, video: Video, listenForActions
  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    video = makeVideo()

    getVideoStub = sandbox.stub(api, "getVideo").returns(Promise.resolve(video))
    dropboxStub = sandbox.stub(libVideo, "saveToDropbox")
    sandbox.stub(api, "getCollections").returns(Promise.resolve({results: []}))

    // silence videojs warnings
    sandbox.stub(libVideo, "videojs")
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderPage = async (props = {}) => {
    let wrapper
    await listenForActions(
      [actions.videos.get.requestType, actions.videos.get.successType],
      () => {
        wrapper = mount(
          <Provider store={store}>
            <VideoDetailPage videoKey={video.key} {...props} />
          </Provider>
        )
      }
    )
    if (!wrapper) {
      throw new Error("Never will happen, make flow happy")
    }
    wrapper.update()
    return wrapper
  }

  it("fetches requirements on load", async () => {
    await renderPage()
    sinon.assert.calledWith(getVideoStub, video.key)
  })

  it("renders the video player", async () => {
    const wrapper = await renderPage()
    const videoPlayerProps = wrapper.find("VideoPlayer").props()
    assert.equal(videoPlayerProps.video, video)
    assert.equal(videoPlayerProps.selectedCorner, "camera1")
  })

  it("shows the video title, description and upload date, and link to collection", async () => {
    const wrapper = await renderPage()
    assert.equal(wrapper.find(".video-title").text(), video.title)
    assert.equal(wrapper.find(".video-description").text(), video.description)
    const formatted = moment(video.created_at).format(MM_DD_YYYY)
    assert.equal(wrapper.find(".upload-date").text(), `Uploaded ${formatted}`)
    const link = wrapper.find(".collection-link")
    assert.equal(link.props().href, makeCollectionUrl(video.collection_key))
    assert.equal(link.text(), video.collection_title)
  })

  it("shows an error message if in an error state", async () => {
    video.status = VIDEO_STATUS_TRANSCODING
    const wrapper = await renderPage()
    assert.equal(
      wrapper.find(".video-message").text(),
      "Video is processing, check back later"
    )
  })

  it("indicates video is processing if it, well, is", async () => {
    video.status = VIDEO_STATUS_ERROR
    const wrapper = await renderPage()
    assert.equal(
      wrapper.find(".video-message").text(),
      "Something went wrong :("
    )
  })

  it("includes the share button and dialog", async () => {
    const wrapper = await renderPage()
    assert.isTrue(wrapper.find(".share").exists())
    assert.isTrue(wrapper.find("ShareVideoDialog").exists())
  })

  it("does not include buttons for privileged functionality when lacking permission", async () => {
    const wrapper = await renderPage({ editable: false })
    assert.isFalse(wrapper.find(".edit").exists())
    assert.isFalse(wrapper.find(".dropbox").exists())
    assert.isFalse(wrapper.find(".delete").exists())
  })

  it("includes the edit button and dialog when the user has correct permissions", async () => {
    const wrapper = await renderPage({ editable: true })
    assert.isTrue(wrapper.find(".edit").exists())
    assert.isTrue(wrapper.find("EditVideoFormDialog").exists())
  })

  it("includes the delete button and dialog when the user has correct permissions", async () => {
    const wrapper = await renderPage({ editable: true })
    assert.isTrue(wrapper.find(".delete").exists())
    assert.isTrue(wrapper.find("DeleteVideoDialog").exists())
  })

  it("includes the dropbox button that triggers dialog when the user has correct permissions", async () => {
    const wrapper = await renderPage({ editable: true })
    const dropboxButton = wrapper.find('.dropbox').hostNodes()
    assert.isTrue(dropboxButton.exists())
    dropboxButton.simulate("click")
    sinon.assert.called(dropboxStub)
  })

  it("has a toolbar whose handler will dispatch an action to open the drawer", async () => {
    const wrapper = await renderPage()
    wrapper.find(".menu-button").simulate("click")
    assert.isTrue(store.getState().commonUi.drawerOpen)
  })

  it("has a Subtitles card", async () => {
    const wrapper = await renderPage()
    assert.isTrue(wrapper.find(".video-subtitle-card").exists())
  })

  it("updates videoSubtitleForm when upload button selects file", async () => {
    const createSubtitleStub = sandbox
      .stub(api, "createSubtitle")
      .returns(Promise.resolve())

    const wrapper = await renderPage({ editable: true })
    const uploadBtn = wrapper.find(".upload-input")
    const file = new File(["foo"], "filename.vtt")
    store.getState().videoUi.videoSubtitleForm.video = video.key
    uploadBtn.prop("onChange")({ target: { files: [file] } })
    assert.equal(store.getState().videoUi.videoSubtitleForm.subtitle, file)

    // iterate on event loop so that createSubtitle is called
    await wait(0)

    sinon.assert.called(createSubtitleStub)
    const formData = createSubtitleStub.args[0][0]

    assert(formData.get("file"), "Missing file")
    assert.equal(formData.get("filename"), "filename.vtt")
    assert.equal(formData.get("collection"), video.collection_key)
    assert.equal(formData.get("video"), video.key)
    assert.equal(formData.get("language"), "en")
  })

  it("deletes a subtitle when delete button is clicked", async () => {
    const deleteStub = sandbox
      .stub(api, "deleteSubtitle")
      .returns(Promise.resolve({}))
    const wrapper = await renderPage({ editable: true })
    const deleteBtns = wrapper.find(".delete-btn")
    assert.equal(deleteBtns.length, 1)
    deleteBtns.at(0).prop("onClick")()
    sinon.assert.calledWith(deleteStub, video.videosubtitle_set[0].id)
  })
})
