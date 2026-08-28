// @flow
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { screen, fireEvent } from "@testing-library/react"
import configureTestStore from "redux-asserts"

import ShareVideoDialog from "./ShareVideoDialog"

import rootReducer from "../../reducers"
import { setSelectedVideoKey } from "../../actions/collectionUi"
import { makeVideo } from "../../factories/video"
import * as videoUiActions from "../../actions/videoUi"
import renderWithProviders from "../../testUtils/renderWithProviders"

const { SET_SHARE_VIDEO_TIME_ENABLED } = videoUiActions.constants

describe("ShareVideoDialog", () => {
  let sandbox, store, hideDialogStub, listenForActions

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    hideDialogStub = sandbox.stub()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (props = {}) => {
    return renderWithProviders(
      <ShareVideoDialog open={true} hideDialog={hideDialogStub} {...props} />,
      { store }
    )
  }

  it("shows the correct content", () => {
    const video = makeVideo()
    renderComponent({ video: video })
    assert.equal(
      screen.getByLabelText("Video URL").value,
      `http://fake/videos/${video.key}/`
    )
    assert.isTrue(
      screen
        .getByLabelText("Embed HTML")
        .value.startsWith(
          `<iframe src="http://fake/videos/${video.key}/embed/"`
        )
    )
    assert.isNull(screen.queryByLabelText("Open edX video URL"))
  })

  it("shows cloudfront_url if the value is set", () => {
    const video = makeVideo()
    const cloudfrontUrl = "https://fake.cloudfront.net/fake_key"
    video.cloudfront_url = cloudfrontUrl
    renderComponent({ video: video })
    assert.equal(
      screen.getByLabelText("Open edX video URL").value,
      cloudfrontUrl
    )
  })
  ;[false, true].forEach(function(checked) {
    it("adds time in seconds to the links only if checkbox is checked", async () => {
      const video = makeVideo()
      renderComponent({ video: video })
      const checkbox = screen.getByRole("checkbox")

      // The checkbox starts unchecked. For the `true` case, click once to
      // check it. For the `false` case, click twice (check, then uncheck)
      // so the explicit "false" dispatch through the real onChange handler
      // is actually exercised rather than just asserting on the untouched
      // default render.
      await listenForActions([SET_SHARE_VIDEO_TIME_ENABLED], () => {
        fireEvent.click(checkbox)
      })
      if (!checked) {
        await listenForActions([SET_SHARE_VIDEO_TIME_ENABLED], () => {
          fireEvent.click(checkbox)
        })
      }
      assert.equal(
        screen.getByLabelText("Video URL").value,
        `http://fake/videos/${video.key}/${checked ? "?start=0" : ""}`
      )
      assert.isTrue(
        screen
          .getByLabelText("Embed HTML")
          .value.startsWith(
            `<iframe src="http://fake/videos/${video.key}/embed/${
              checked ? "?start=0" : ""
            }"`
          )
      )
    })
  })

  it("gets the video key from a video object provided as a prop", () => {
    const video = makeVideo()
    renderComponent({ video: video })
    assert.equal(
      screen.getByLabelText("Video URL").value,
      `http://fake/videos/${video.key}/`
    )
  })

  it("gets the video key from the collection UI state if a video object isn't passed in", () => {
    const videoKey = "video-key"
    store.dispatch(setSelectedVideoKey(videoKey))
    renderComponent({ video: null })
    assert.equal(
      screen.getByLabelText("Video URL").value,
      `http://fake/videos/${videoKey}/`
    )
  })

  it("gets the video from the state using SelectedVideoKey if a video object isn't passed in", () => {
    const url = "cloudfront-url"

    const video = makeVideo()
    video["cloudfront_url"] = url
    store.dispatch(setSelectedVideoKey(video.key))
    renderComponent({
      video:      null,
      collection: { videos: [video] }
    })
    assert.equal(screen.getByLabelText("Open edX video URL").value, url)
  })
})
