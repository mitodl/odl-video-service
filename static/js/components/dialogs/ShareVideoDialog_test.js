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
    const { container } = renderComponent({ video: video })
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
    assert.isNull(container.querySelector("#video-openedx-url"))
  })

  it("shows cloudfront_url if the value is set", () => {
    const video = makeVideo()
    const cloudfrontUrl = "https://fake.cloudfront.net/fake_key"
    video.cloudfront_url = cloudfrontUrl
    const { container } = renderComponent({ video: video })
    assert.equal(
      container.querySelector("#video-openedx-url").value,
      cloudfrontUrl
    )
  })
  ;[false, true].forEach(function(checked) {
    it("adds time in seconds to the links only if checkbox is checked", async () => {
      const video = makeVideo()
      renderComponent({ video: video })
      if (checked) {
        await listenForActions([SET_SHARE_VIDEO_TIME_ENABLED], () => {
          fireEvent.click(screen.getByRole("checkbox"))
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
    const { container } = renderComponent({
      video:      null,
      collection: { videos: [video] }
    })
    assert.equal(container.querySelector("#video-openedx-url").value, url)
  })
})
