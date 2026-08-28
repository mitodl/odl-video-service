// @flow
import React from "react"
import sinon from "sinon"
import { render, screen } from "@testing-library/react"
import { assert } from "chai"
import configureTestStore from "redux-asserts"

import rootReducer from "../reducers"
import * as libVideo from "../lib/video"
import VideoEmbedPage from "./VideoEmbedPage"
import { VideoEmbedPage as UnconnectedVideoEmbedPage } from "./VideoEmbedPage"
import { makeVideo } from "../factories/video"
import renderWithProviders from "../testUtils/renderWithProviders"
import type { Video } from "../flow/videoTypes"

describe("VideoEmbedPage", () => {
  let sandbox, store, video: Video

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    video = makeVideo()
    // silence videojs warnings

    sandbox.stub(libVideo, "videojs")
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderPage = async (props = {}) => {
    return renderWithProviders(<VideoEmbedPage video={video} {...props} />, {
      store
    })
  }

  describe("when video is processing", () => {
    beforeEach(() => {
      sandbox
        .stub(UnconnectedVideoEmbedPage.prototype, "getVideoStatus")
        .returns("PROCESSING")
      render(<UnconnectedVideoEmbedPage video={video} />)
    })

    it("renders processing message", () => {
      assert.isNotNull(screen.getByText("Video processing..."))
    })
  })

  describe("when video has error", () => {
    beforeEach(() => {
      sandbox
        .stub(UnconnectedVideoEmbedPage.prototype, "getVideoStatus")
        .returns("ERROR")
      render(<UnconnectedVideoEmbedPage video={video} />)
    })

    it("renders error message", () => {
      assert.isNotNull(screen.getByText("Sorry, this video has an error."))
    })
  })

  it("passes the correct video and selectedCorner to VideoPlayer", async () => {
    // VideoPlayer doesn't expose the `video` or `selectedCorner` props it
    // receives anywhere RTL-observable (no title/source text in its DOM
    // output) unless the video is a multiangle video, in which case it
    // renders one camera-box canvas per corner and marks the one matching
    // `selectedCorner` with a "camera-box-selected" class. Forcing
    // multiangle here is a real, RTL-observable behavior of VideoPlayer's
    // own render output (not a prop-inspection shortcut) that verifies
    // VideoEmbedPage wires the video and the default corner ("camera1",
    // from the videoUi reducer's initial state) down correctly.
    video.multiangle = true
    const { container } = await renderPage()
    const selectedCameraBox = container.querySelector(
      "#camera1.camera-box-selected"
    )
    assert.isNotNull(
      selectedCameraBox,
      "expected the camera1 canvas to be marked selected by default"
    )
  })
})
