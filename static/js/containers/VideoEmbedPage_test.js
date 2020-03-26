// @flow
import React from "react"
import sinon from "sinon"
import { mount, shallow } from "enzyme"
import { assert } from "chai"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"

import rootReducer from "../reducers"
import * as libVideo from "../lib/video"
import VideoEmbedPage from "./VideoEmbedPage"
import { VideoEmbedPage as UnconnectedVideoEmbedPage } from "./VideoEmbedPage"
import { makeVideo } from "../factories/video"
import type { Video } from "../flow/videoTypes"

describe("VideoEmbedPage", () => {
  let sandbox, store, video: Video

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
    video = makeVideo()
    // silence videojs warnings

    const playerStub = {
      el_: {
        style:         {},
        dispatchEvent: sandbox.stub()
      },
      tracks:       [],
      on:           sandbox.stub(),
      tech_:        {},
      reset:        sandbox.stub().returns(playerStub),
      src:          sandbox.stub().returns(playerStub),
      fluid:        sandbox.stub().returns(playerStub),
      width:        sandbox.stub(),
      height:       sandbox.stub(),
      hotkeys:      sandbox.stub(),
      duration:     () => 2400.0,
      videoWidth:   () => 640,
      videoHeight:  () => 360,
      currentWidth: () => 1280,
      textTracks:   function() {
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
    return mount(
      <Provider store={store}>
        <VideoEmbedPage video={video} {...props} />
      </Provider>
    )
  }

  describe("when video is processing", () => {
    let wrapper
    beforeEach(() => {
      sandbox
        .stub(UnconnectedVideoEmbedPage.prototype, "getVideoStatus")
        .returns("PROCESSING")
      const element = <UnconnectedVideoEmbedPage video={video} />
      wrapper = shallow(element)
    })

    it("renders processing message", () => {
      assert.isTrue(wrapper.find(".processing-message").exists())
    })
  })

  describe("when video has error", () => {
    let wrapper
    beforeEach(() => {
      sandbox
        .stub(UnconnectedVideoEmbedPage.prototype, "getVideoStatus")
        .returns("ERROR")
      const element = <UnconnectedVideoEmbedPage video={video} />
      wrapper = shallow(element)
    })

    it("renders error message", () => {
      assert.isTrue(wrapper.find(".error-message").exists())
    })
  })

  it("renders a VideoPlayer component", async () => {
    const wrapper = await renderPage()
    const videoPlayerProps = wrapper.find("VideoPlayer").props()
    assert.equal(videoPlayerProps.video, video)
    assert.equal(videoPlayerProps.selectedCorner, "camera1")
  })
})
