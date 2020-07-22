// @flow
import React from "react"
import sinon from "sinon"
import moment from "moment"
import { mount, shallow } from "enzyme"
import { assert } from "chai"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"

import VideoDetailPage from "./VideoDetailPage"
import { VideoDetailPage as UnwrappedVideoDetailPage } from "./VideoDetailPage"

import * as api from "../lib/api"
import { actions } from "../actions"
import * as toastActions from "../actions/toast"
import * as videoUiActions from "../actions/videoUi"
import rootReducer from "../reducers"
import * as libVideo from "../lib/video"
import { makeVideo } from "../factories/video"
import { makeCollectionUrl } from "../lib/urls"
import {
  DIALOGS,
  MM_DD_YYYY,
  VIDEO_STATUS_TRANSCODING,
  VIDEO_STATUS_ERROR
} from "../constants"

import type { Video } from "../flow/videoTypes"

describe("VideoDetailPage", () => {
  let sandbox, store, getVideoStub, dropboxStub, video: Video, listenForActions

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    video = makeVideo()

    getVideoStub = sandbox.stub(api, "getVideo").returns(Promise.resolve(video))
    dropboxStub = sandbox.stub(libVideo, "saveToDropbox")
    sandbox
      .stub(api, "getCollections")
      .returns(Promise.resolve({ results: [] }))

    sandbox.stub(libVideo, "videojs")
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderPage = async (props = {}) => {
    let wrapper
    await listenForActions(
      [
        actions.videos.get.requestType,
        actions.videos.get.successType,
        videoUiActions.constants.SET_CURRENT_VIDEO_KEY
      ],
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

  const renderPageShallow = (props = {}) => {
    const propsWithDefaults = {
      dispatch:    sandbox.spy(),
      video,
      videoKey:    video.key,
      needsUpdate: false,
      commonUi:    {},
      videoUi:     {},
      showDialog:  sandbox.spy(),
      isAdmin:     false,
      ...props
    }
    return shallow(<UnwrappedVideoDetailPage {...propsWithDefaults} />)
  }

  it("fetches requirements on load", async () => {
    await renderPage()
    sinon.assert.calledWith(getVideoStub, video.key)
  })

  it("sets currentVideoKey", async () => {
    await renderPage()
    assert.equal(store.getState().videoUi.currentVideoKey, video.key)
  })

  it("renders the video player", () => {
    const videoUi = { corner: "someCorner" }
    const pageWrapper = renderPageShallow({ videoUi })
    const pageInstance = pageWrapper.instance()
    const overlayChildrenStub = sandbox.stub(
      pageInstance,
      "renderOverlayChildren"
    )
    const videoPlayerWrapper = shallow(pageInstance.renderVideoPlayer(video))
    const videoPlayerProps = videoPlayerWrapper.find("#video-player").props()
    assert.equal(videoPlayerProps.video, video)
    assert.equal(videoPlayerProps.selectedCorner, videoUi.corner)
    assert.equal(
      videoPlayerProps.overlayChildren,
      overlayChildrenStub.returnValues[0]
    )
  })

  describe("renderOverlayChildren", () => {
    it("includes renderAnalyticsOverlay result", () => {
      const pageWrapper = renderPageShallow()
      const pageInstance = pageWrapper.instance()
      const renderAnalyticsOverlayStub = sandbox.stub(
        pageInstance,
        "renderAnalyticsOverlay"
      )
      const actualOverlayChildren = pageInstance.renderOverlayChildren()
      assert.equal(
        actualOverlayChildren[0],
        renderAnalyticsOverlayStub.returnValues[0]
      )
    })
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
    const wrapper = await renderPage({ isAdmin: false })
    assert.isFalse(wrapper.find(".analytics").exists())
    assert.isFalse(wrapper.find(".edit").exists())
    assert.isFalse(wrapper.find(".dropbox").exists())
    assert.isFalse(wrapper.find(".delete").exists())
  })

  describe("analytics button", async () => {
    const _findAnalyticsButton = wrapper => {
      return wrapper.find(".analytics").hostNodes()
    }

    it("includes the analytics button when the user has correct permissions", async () => {
      const wrapper = await renderPage({ isAdmin: true })
      assert.isTrue(_findAnalyticsButton(wrapper).exists())
    })

    it("onClick calls toggleAnalyticsOverlay", async () => {
      const wrapper = await renderPage({ isAdmin: true })
      const pageInstance = wrapper.find("VideoDetailPage").instance()
      const toggleStub = sandbox.stub(pageInstance, "toggleAnalyticsOverlay")
      const analyticsButton = _findAnalyticsButton(wrapper)
      sinon.assert.notCalled(toggleStub)
      analyticsButton.simulate("click")
      sinon.assert.called(toggleStub)
    })
  })

  it("includes the edit button and dialog when the user has correct permissions", async () => {
    const wrapper = await renderPage({ isAdmin: true })
    assert.isTrue(wrapper.find(".edit").exists())
    assert.isTrue(wrapper.find("EditVideoFormDialog").exists())
  })

  it("includes the delete button and dialog when the user has correct permissions", async () => {
    const wrapper = await renderPage({ isAdmin: true })
    assert.isTrue(wrapper.find(".delete").exists())
    assert.isTrue(wrapper.find("DeleteVideoDialog").exists())
  })

  it("includes the dropbox button that triggers dialog when the user has correct permissions", async () => {
    const wrapper = await renderPage({ isAdmin: true })
    const dropboxButton = wrapper.find(".dropbox").hostNodes()
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

  describe("when upload button selects file", () => {
    let createSubtitleStub, wrapper, file

    beforeEach(async () => {
      createSubtitleStub = sandbox
        .stub(api, "createSubtitle")
        .returns(Promise.resolve())
      wrapper = await renderPage({ isAdmin: true })
      const uploadBtn = wrapper.find(".upload-input")
      file = new File(["foo"], "filename.vtt")
      store.getState().videoUi.videoSubtitleForm.video = video.key
      await listenForActions(
        [
          actions.videoSubtitles.post.requestType,
          toastActions.constants.ADD_MESSAGE,
          videoUiActions.constants.SET_UPLOAD_SUBTITLE
        ],
        () => {
          uploadBtn.prop("onChange")({ target: { files: [file] } })
        }
      )
    })

    it("updates videoSubtitleForm", () => {
      assert.equal(store.getState().videoUi.videoSubtitleForm.subtitle, file)
      sinon.assert.called(createSubtitleStub)
      const formData = createSubtitleStub.args[0][0]
      assert(formData.get("file"), "Missing file")
      assert.equal(formData.get("filename"), "filename.vtt")
      assert.equal(formData.get("collection"), video.collection_key)
      assert.equal(formData.get("video"), video.key)
      assert.equal(formData.get("language"), "en")
    })

    it("adds toast message", () => {
      assert.deepEqual(store.getState().toast.messages, [
        {
          key:     "subtitles-uploaded",
          content: "Subtitles uploaded",
          icon:    "check"
        }
      ])
    })
  })

  describe("when subtitle delete button is clicked", () => {
    let showDeleteSubtitlesDialogStub

    beforeEach(async () => {
      const wrapper = await renderPage({ isAdmin: true })
      const instance = wrapper.find("VideoDetailPage").instance()
      showDeleteSubtitlesDialogStub = sandbox.stub(
        instance,
        "showDeleteSubtitlesDialog"
      )
      const deleteBtns = wrapper.find(".delete-btn")
      deleteBtns.at(0).prop("onClick")()
      sinon.assert.calledWith(
        showDeleteSubtitlesDialogStub,
        video.videosubtitle_set[0].id
      )
    })
  })

  describe("showDeleteSubtitlesDialog", () => {
    let stubs, instance
    const subtitlesKey = "someSubtitleKey"
    beforeEach(() => {
      stubs = {
        dispatch:               sandbox.stub(),
        showDialog:             sandbox.stub(),
        setCurrentSubtitlesKey: sandbox.stub(
          actions.videoUi,
          "setCurrentSubtitlesKey"
        )
      }
      const props = {
        dispatch:   stubs.dispatch,
        showDialog: stubs.showDialog,
        isAdmin:    true
      }
      const wrapper = shallow(<UnwrappedVideoDetailPage {...props} />)
      instance = wrapper.instance()
      instance.showDeleteSubtitlesDialog(subtitlesKey)
    })

    it("sets currentSubtitlesKey", () => {
      sinon.assert.calledWith(stubs.setCurrentSubtitlesKey, { subtitlesKey })
      sinon.assert.calledWith(
        stubs.dispatch,
        stubs.setCurrentSubtitlesKey.returnValues[0]
      )
    })

    it("calls showDialog", () => {
      sinon.assert.calledWith(stubs.showDialog, DIALOGS.DELETE_SUBTITLES)
    })
  })

  describe("renderAnalyticsOverlay", () => {
    let pageInstance, overlayEl

    beforeEach(async () => {
      pageInstance = renderPageShallow({
        videoUi: {
          analyticsOverlayIsVisible: true,
          videoTime:                 42,
          duration:                  42
        }
      }).instance()
      const overlayWrapper = shallow(pageInstance.renderAnalyticsOverlay())
      overlayEl = overlayWrapper.find("#video-analytics-overlay")
    })

    it("renders analytics overlay with expected props", () => {
      assert.equal(overlayEl.prop("video"), pageInstance.props.video)
      assert.equal(
        overlayEl.prop("currentTime"),
        pageInstance.props.videoUi.videoTime
      )
      assert.equal(
        overlayEl.prop("duration"),
        pageInstance.props.videoUi.duration
      )
    })

    it("passes setVideoTime", () => {
      const setVideoTimeStub = sandbox.stub(pageInstance, "setVideoTime")
      overlayEl.prop("setVideoTime")("argA", "argB")
      sinon.assert.calledWith(setVideoTimeStub, "argA", "argB")
    })

    it("passes closeOverlay", () => {
      assert.equal(
        overlayEl.prop("onClose"),
        pageInstance.toggleAnalyticsOverlay
      )
    })

    it("passes showCloseButton", () => {
      assert.isTrue(overlayEl.prop("showCloseButton"))
    })
  })

  it("has toast message", async () => {
    const wrapper = await renderPage()
    assert.isTrue(wrapper.find("Connect(ToastOverlay)").exists())
  })
})
