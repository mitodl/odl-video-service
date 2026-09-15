// @flow
import React from "react"
import sinon from "sinon"
import moment from "moment"
import { assert } from "chai"
import { render, fireEvent } from "@testing-library/react"
import configureTestStore from "redux-asserts"

import VideoDetailPage from "./VideoDetailPage"
import { VideoDetailPage as UnwrappedVideoDetailPage } from "./VideoDetailPage"
import ConnectedVideoPlayerDefault from "../components/VideoPlayer"
import { ConnectedVideoAnalyticsOverlay } from "./VideoAnalyticsOverlay"

import * as api from "../lib/api"
import { actions } from "../actions"
import * as toastActions from "../actions/toast"
import * as videoUiActions from "../actions/videoUi"
import { SHOW_DIALOG } from "../actions/commonUi"
import rootReducer from "../reducers"
import * as libVideo from "../lib/video"
import { makeVideo } from "../factories/video"
import { makeCollectionUrl } from "../lib/urls"
import renderWithProviders from "../testUtils/renderWithProviders"
import {
  DIALOGS,
  MM_DD_YYYY,
  VIDEO_STATUS_TRANSCODING,
  VIDEO_STATUS_ERROR
} from "../constants"

import type { Video } from "../flow/videoTypes"

describe("VideoDetailPage", () => {
  let sandbox,
    store,
    getVideoStub,
    dropboxStub,
    video: Video,
    listenForActions,
    playerStub

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
    // Mounting the (real, connected) analytics overlay for the first time
    // -- i.e. toggling analyticsOverlayIsVisible true -- triggers
    // withVideoAnalytics' componentDidUpdate -> videoAnalytics.get fetch.
    // Left permanently pending: nothing below asserts on the fetched data
    // itself (that's AnalyticsPane/VideoAnalyticsOverlay's own test
    // coverage), only on the request firing and on the outer wiring, so
    // there's nothing to gain from resolving it and real risk (an
    // unmocked-shape success payload reaching AnalyticsPane) in doing so.
    sandbox.stub(api, "getVideoAnalytics").returns(new Promise(() => {}))

    // Bare (no .returns()) is not enough for this file: unlike VideoPlayer's
    // own tests, VideoDetailPage re-renders its <VideoPlayer> child (a new
    // element, same underlying player) on every store dispatch that touches
    // videoUi/videos state -- toggling the analytics overlay, opening the
    // drawer, uploading a subtitle, etc. all trigger it. Each such re-render
    // runs VideoPlayer's componentDidUpdate -> updateSubtitles(), which calls
    // this.player.textTracks()/addRemoteTextTrack()/removeRemoteTextTrack().
    // Without those, most tests below throw
    // "this.player.textTracks is not a function" the moment they dispatch
    // anything post-mount. Verified empirically (spike B) -- see the task
    // report. dispose is required too: RTL unmounts after every test, so
    // componentWillUnmount's real this.player.dispose() call now runs.
    playerStub = {
      tracks:      [],
      currentTime: sandbox.stub(),
      dispose:     sandbox.stub(),
      textTracks:  function() {
        return this.tracks
      },
      removeRemoteTextTrack: function(track) {
        this.tracks.splice(this.tracks.indexOf(track), 1)
      },
      addRemoteTextTrack: function(track) {
        this.tracks.push({ src: track.src, addEventListener: function() {} })
      }
    }
    sandbox.stub(libVideo, "videojs").returns(playerStub)
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderPage = async (props = {}) => {
    let result
    await listenForActions(
      [
        actions.videos.get.requestType,
        actions.videos.get.successType,
        videoUiActions.constants.SET_CURRENT_VIDEO_KEY
      ],
      () => {
        result = renderWithProviders(
          <VideoDetailPage videoKey={video.key} {...props} />,
          { store }
        )
      }
    )
    if (!result) {
      throw new Error("Never will happen, make flow happy")
    }
    return result
  }

  // Renders the unconnected class directly, with a ref callback to capture
  // the instance -- for tests that only care about a method's own behavior
  // and need no store or child rendering at all (mirrors the old
  // renderPageShallow, which used `shallow()` + `.instance()` for exactly
  // this purpose).
  const renderUnwrappedWithRef = (props = {}) => {
    let instance
    render(
      <UnwrappedVideoDetailPage
        ref={r => {
          instance = r
        }}
        {...props}
      />
    )
    return instance
  }

  it("fetches requirements on load", async () => {
    await renderPage()
    sinon.assert.calledWith(getVideoStub, video.key)
  })

  it("sets currentVideoKey", async () => {
    await renderPage()
    assert.equal(store.getState().videoUi.currentVideoKey, video.key)
  })

  it("renders the video player", async () => {
    // Pinned so the DOM shape below (no camera-box markup) is deterministic
    // -- makeVideo()'s multiangle is a coin flip, and multiangle-driven
    // markup is irrelevant to what this test checks (VideoPlayer_test.js
    // owns that coverage).
    video.multiangle = false

    // Spying on the *connected* default export's prototype.render, not the
    // pre-connect class (which isn't exported) -- confirmed empirically
    // (spike A, see task report) that react-redux v5's Connect wrapper is a
    // real ES6 class here, and `this.props` on that instance is exactly the
    // ownProps VideoDetailPage passed to <VideoPlayer>, i.e. video,
    // cornerFunc, selectedCorner, overlayChildren, videoPlayerRef, id.
    const spy = sandbox.spy(ConnectedVideoPlayerDefault.prototype, "render")
    const { container } = await renderPage()

    assert.equal(spy.lastCall.thisValue.props.video, video)

    store.dispatch(actions.videoUi.updateVideoJsSync("someCorner"))
    assert.equal(spy.lastCall.thisValue.props.selectedCorner, "someCorner")

    // overlayChildren: rather than stubbing renderOverlayChildren (no seam
    // to reach it on a HOC-connected instance), assert the wiring end to end
    // through real DOM -- this is what renderVideoPlayer -> overlayChildren
    // -> renderOverlayChildren -> renderAnalyticsOverlay actually produces.
    assert.isNull(container.querySelector(".analytics-overlay-container"))
    store.dispatch(actions.videoUi.toggleAnalyticsOverlay())
    assert.isNotNull(container.querySelector(".analytics-overlay-container"))
  })

  it("shows the video title, description and upload date, and link to collection", async () => {
    const { container } = await renderPage()
    assert.equal(
      container.querySelector(".video-title").textContent,
      video.title
    )
    assert.equal(
      container.querySelector(".video-description").textContent,
      video.description
    )
    const formatted = moment(video.created_at).format(MM_DD_YYYY)
    assert.equal(
      container.querySelector(".upload-date").textContent,
      `Uploaded ${formatted}`
    )
    const link = container.querySelector(".collection-link")
    assert.equal(
      link.getAttribute("href"),
      makeCollectionUrl(video.collection_key)
    )
    assert.equal(link.textContent, video.collection_title)
  })

  it("renders the description as markup, not as escaped text", async () => {
    // Descriptions are rich text, sanitized server-side on write (ui/html.py),
    // so the page injects them rather than escaping them.
    video.description = '<p>see the <a href="https://mit.edu">notes</a></p>'
    video.description_format = "html"
    const { container } = await renderPage()
    const description = container.querySelector(".video-description")
    assert.equal(description.querySelectorAll("a").length, 1)
    assert.equal(
      description.querySelector("a").getAttribute("href"),
      "https://mit.edu"
    )
    assert.equal(description.textContent, "see the notes")
  })

  it("renders a plain-text description as text, keeping its line breaks", async () => {
    /*
     * The format on the record decides this, not the value. Injecting a legacy
     * plain-text description as markup is what truncates it: a browser reads
     * `<b to a` as an unterminated tag and drops everything after it.
     */
    video.description = "Compare <b to a.\nSecond line."
    video.description_format = "text"
    const { container } = await renderPage()
    const description = container.querySelector(".video-description")
    assert.equal(description.textContent, "Compare <b to a.\nSecond line.")
    assert.lengthOf(description.querySelectorAll("b"), 0)
    assert.isTrue(description.classList.contains("description-plain-text"))
  })

  // These two test names were swapped relative to what they actually assert
  // in the pre-conversion Enzyme file -- carried-over naming bug, not
  // introduced here. Fixed here since it's a pure rename (dossier flagged,
  // see commit message): the first exercises the processing branch, the
  // second the error branch.
  it("indicates video is processing if it, well, is", async () => {
    video.status = VIDEO_STATUS_TRANSCODING
    const { container } = await renderPage()
    assert.equal(
      container.querySelector(".video-message").textContent,
      "Video is processing, check back later"
    )
  })

  it("shows an error message if in an error state", async () => {
    video.status = VIDEO_STATUS_ERROR
    const { container } = await renderPage()
    assert.equal(
      container.querySelector(".video-message").textContent,
      "Something went wrong :("
    )
  })

  it("includes the share button and dialog", async () => {
    const { container } = await renderPage()
    assert.isNotNull(container.querySelector(".share"))
    assert.isNotNull(container.querySelector("#share-video-dialog"))
  })

  it("does not include buttons for privileged functionality when lacking permission", async () => {
    const { container } = await renderPage({ isAdmin: false })
    assert.isNull(container.querySelector(".analytics"))
    assert.isNull(container.querySelector(".edit"))
    assert.isNull(container.querySelector(".dropbox"))
    assert.isNull(container.querySelector(".delete"))
  })

  describe("analytics button", () => {
    it("includes the analytics button when the user has correct permissions", async () => {
      const { container } = await renderPage({ isAdmin: true })
      assert.isNotNull(container.querySelector(".analytics"))
    })

    it("onClick calls toggleAnalyticsOverlay", async () => {
      // Behavioral rewrite: the old test drilled to the instance via
      // wrapper.find("VideoDetailPage").instance() (no RTL analog) to stub
      // toggleAnalyticsOverlay and assert it was called. This asserts the
      // real, stronger, user-visible effect instead -- the store state the
      // handler actually flips.
      const { container } = await renderPage({ isAdmin: true })
      assert.isFalse(store.getState().videoUi.analyticsOverlayIsVisible)
      await listenForActions(
        [
          videoUiActions.constants.TOGGLE_ANALYTICS_OVERLAY,
          // Mounting <ConnectedVideoAnalyticsOverlay> for the first time
          // (analyticsOverlayIsVisible flips true) triggers its own
          // componentDidUpdate -> needsUpdate -> videoAnalytics.get fetch.
          actions.videoAnalytics.get.requestType
        ],
        () => {
          fireEvent.click(container.querySelector(".analytics"))
        }
      )
      assert.isTrue(store.getState().videoUi.analyticsOverlayIsVisible)
    })
  })

  it("includes the edit button and dialog when the user has correct permissions", async () => {
    const { container } = await renderPage({ isAdmin: true })
    assert.isNotNull(container.querySelector(".edit"))
    assert.isNotNull(container.querySelector("#edit-video-form-dialog"))
  })

  it("includes the delete button and dialog when the user has correct permissions", async () => {
    const { container } = await renderPage({ isAdmin: true })
    assert.isNotNull(container.querySelector(".delete"))
    assert.isNotNull(container.querySelector("#delete-video-dialog"))
  })

  it("includes the dropbox button that triggers dialog when the user has correct permissions", async () => {
    const { container } = await renderPage({ isAdmin: true })
    const dropboxButton = container.querySelector(".dropbox")
    assert.isNotNull(dropboxButton)
    fireEvent.click(dropboxButton)
    sinon.assert.called(dropboxStub)
  })

  it("has a toolbar whose handler will dispatch an action to open the drawer", async () => {
    const { container } = await renderPage()
    fireEvent.click(container.querySelector(".menu-button"))
    assert.isTrue(store.getState().commonUi.drawerOpen)
  })

  it("has a Subtitles card", async () => {
    const { container } = await renderPage()
    assert.isNotNull(container.querySelector(".video-subtitle-card"))
  })

  describe("when upload button selects file", () => {
    let createSubtitleStub, container, file

    beforeEach(async () => {
      createSubtitleStub = sandbox
        .stub(api, "createSubtitle")
        .returns(Promise.resolve())
      ;({ container } = await renderPage({ isAdmin: true }))
      const uploadInput = container.querySelector(
        ".video-subtitle-card .upload-input"
      )
      file = new File(["foo"], "filename.vtt")
      // Pre-existing test smell carried over unchanged: mutates the redux
      // state object in place. Works only because nothing in this chain
      // freezes state.
      store.getState().videoUi.videoSubtitleForm.video = video.key
      await listenForActions(
        [
          actions.videoSubtitles.post.requestType,
          actions.videoSubtitles.post.successType,
          actions.videos.get.requestType,
          actions.videos.get.successType,
          actions.collections.get.failureType,
          toastActions.constants.ADD_MESSAGE,
          videoUiActions.constants.SET_UPLOAD_SUBTITLE
        ],
        () => {
          fireEvent.change(uploadInput, { target: { files: [file] } })
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
    it("sets currentSubtitlesKey and opens the delete-subtitles dialog", async () => {
      // Behavioral rewrite: the old test drilled to the instance via
      // wrapper.find("VideoDetailPage").instance() to stub
      // showDeleteSubtitlesDialog and assert it was called with the
      // subtitle's id, then never even inspected the DOM effect. This
      // fires a real click and asserts the two real effects
      // showDeleteSubtitlesDialog produces: the store key it sets, and the
      // dialog it opens.
      const { container } = await renderPage({ isAdmin: true })
      const deleteBtn = container.querySelectorAll(".delete-btn")[0]
      await listenForActions(
        [videoUiActions.constants.SET_CURRENT_SUBTITLES_KEY, SHOW_DIALOG],
        () => {
          fireEvent.click(deleteBtn)
        }
      )
      assert.equal(
        store.getState().videoUi.currentSubtitlesKey,
        video.videosubtitle_set[0].id
      )
      assert.isTrue(
        container
          .querySelector("#delete-subtitles-dialog")
          .classList.contains("mdc-dialog--open")
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
      // No `video` prop -- VideoDetailPage.render()'s `if (!video) return
      // null` guard means this mounts no children (no store/Provider
      // needed), same shape as the old shallow-render props object.
      instance = renderUnwrappedWithRef({
        dispatch:   stubs.dispatch,
        showDialog: stubs.showDialog,
        isAdmin:    true
      })
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
    let spy

    beforeEach(async () => {
      // Same technique as "renders the video player" above, applied to the
      // other connected child this container builds props for by hand.
      // Confirmed empirically (spike A) that this fires and that
      // `this.props` on the Connect instance is exactly the ownProps
      // VideoDetailPage passed to <ConnectedVideoAnalyticsOverlay>.
      spy = sandbox.spy(ConnectedVideoAnalyticsOverlay.prototype, "render")
      await renderPage()
      store.dispatch(actions.videoUi.toggleAnalyticsOverlay())
      store.dispatch(actions.videoUi.setVideoTime(42))
      store.dispatch(actions.videoUi.setVideoDuration(42))
    })

    it("renders analytics overlay with expected props", () => {
      assert.equal(spy.lastCall.thisValue.props.video, video)
      assert.equal(spy.lastCall.thisValue.props.currentTime, 42)
      assert.equal(spy.lastCall.thisValue.props.duration, 42)
    })

    it("passes setVideoTime", () => {
      // Stronger than the original (which only proved setVideoTime was
      // *called*): this is the same videoPlayerRef contract
      // VideoPlayer_test.js's "exposes setCurrentTime through
      // videoPlayerRef" documents, exercised end to end through the real
      // player stub.
      spy.lastCall.thisValue.props.setVideoTime(99)
      sinon.assert.calledWith(playerStub.currentTime, 99)
    })

    it("passes closeOverlay", () => {
      // Behavioral rewrite: rather than an identity check against an
      // instance method (no instance in play here), call the captured prop
      // and assert the real effect it produces.
      assert.isTrue(store.getState().videoUi.analyticsOverlayIsVisible)
      spy.lastCall.thisValue.props.onClose()
      assert.isFalse(store.getState().videoUi.analyticsOverlayIsVisible)
    })

    it("passes showCloseButton", () => {
      assert.isTrue(spy.lastCall.thisValue.props.showCloseButton)
    })
  })

  it("has toast message", async () => {
    // Reinterpreted: the old assertion only proved a <ToastOverlay/>
    // element was present in the tree (it renders null with no messages,
    // so this was never a DOM-observable fact and has no RTL equivalent).
    // This seeds a real message and asserts it actually surfaces.
    const { container } = await renderPage()
    store.dispatch(
      actions.toast.addMessage({
        message: { key: "x", content: "Hello", icon: "check" }
      })
    )
    assert.isNotNull(container.querySelector(".toast-overlay"))
    assert.isNotNull(container.querySelector(".toast-message"))
  })
})
