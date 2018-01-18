// @flow
import React from "react"
import sinon from "sinon"
import { mount } from "enzyme"
import { assert } from "chai"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"

import rootReducer from "../reducers"
import * as libVideo from "../lib/video"
import VideoEmbedPage from "./VideoEmbedPage"
import { makeVideo } from "../factories/video"
import type { Video } from "../flow/videoTypes"

describe("VideoEmbedPage", () => {
  let sandbox, store, video: Video

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
    video = makeVideo()
    // silence videojs warnings
    sandbox.stub(libVideo, "videojs")
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderPage = async (props = {}) => {
    return mount(
      <Provider store={store}>
        <VideoEmbedPage video={video} {...props} />
      </Provider>
    )
  }

  it("renders a VideoPlayer component", async () => {
    const wrapper = await renderPage()
    const videoPlayerProps = wrapper.find("VideoPlayer").props()
    assert.equal(videoPlayerProps.video, video)
    assert.equal(videoPlayerProps.selectedCorner, "camera1")
  })
})
