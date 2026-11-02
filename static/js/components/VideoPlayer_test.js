// @flow
import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { fireEvent } from "@testing-library/react"
import { URLSearchParams } from "url"
import configureTestStore from "redux-asserts"
import VideoPlayer from "./VideoPlayer"
import { VideoPlayerController } from "../lib/video_player_controller"
import {
  makeVideo,
  makeVideoSource,
  makeVideoSubtitle
} from "../factories/video"
import * as libVideo from "../lib/video"
import { actions } from "../actions"
import { FULLSCREEN_API } from "../util/fullscreen_api"
import { CANVASES } from "../constants"
import { expect } from "../util/test_utils"
import rootReducer from "../reducers"
import renderWithProviders from "../testUtils/renderWithProviders"
import { makePlayerStub } from "../testUtils/playerStub"

global.URLSearchParams = URLSearchParams

describe("VideoPlayer", () => {
  let video,
    videojsStub,
    sandbox,
    cornerFunction,
    playerStub,
    store,
    dispatchSpy

  const renderPlayer = (props = {}) =>
    renderWithProviders(
      <VideoPlayer
        video={video}
        cornerFunc={cornerFunction}
        selectedCorner={Object.keys(CANVASES)[0]}
        {...props}
      />,
      { store }
    )

  // Invoke the onPlayerReady callback VideoPlayer passed to videojs, the way
  // video.js itself would. Returns the fake `this` so tests can fire the
  // handlers it registered.
  const readyPlayer = () => {
    const fakeReadyThis = {
      enableTouchActivity: sandbox.stub(),
      hotkeys:             sandbox.stub(),
      currentTime:         sandbox.stub(),
      on:                  sandbox.stub(),
      tech_:               playerStub.tech_
    }
    videojsStub.firstCall.args[2].call(fakeReadyThis)
    return fakeReadyThis
  }

  const fireReadyEvent = (fakeReadyThis, event) => {
    const call = fakeReadyThis.on.getCalls().find(c => c.args[0] === event)
    assert.isOk(call, `no handler registered for ${event}`)
    call.args[1].call(fakeReadyThis)
  }

  const firePlayerEvent = event => {
    const call = playerStub.on.getCalls().find(c => c.args[0] === event)
    assert.isOk(call, `no handler registered for ${event}`)
    call.args[1]()
  }

  // Capture every `new Image()` the component makes. `new Image()` in module
  // code resolves through the global scope, not through `window`, so the stub
  // has to go on `global`.
  const captureImages = () => {
    const images = []
    sandbox.stub(global, "Image").callsFake(function() {
      images.push(this)
    })
    return images
  }

  beforeEach(() => {
    video = makeVideo()
    sandbox = sinon.createSandbox()
    sandbox.stub(global, "setTimeout")
    cornerFunction = sandbox.stub()
    playerStub = makePlayerStub(sandbox)
    videojsStub = sandbox.stub(libVideo, "videojs").returns(playerStub)
    store = configureTestStore(rootReducer)
    dispatchSpy = sandbox.spy(store, "dispatch")
  })

  afterEach(() => {
    sandbox.restore()
  })
  ;[true, false].forEach(function(embed) {
    [true, false].forEach(function(multiangle) {
      it("uses videojs on mount with the right arguments", () => {
        video.multiangle = multiangle
        renderPlayer({ embed })
        sinon.assert.called(videojsStub)
        const args = videojsStub.firstCall.args
        assert.equal(args[0].tagName, "VIDEO")
        assert.deepEqual(args[1], {
          autoplay:    false,
          poster:      video.videothumbnail_set[0].cloudfront_url,
          controls:    true,
          fluid:       embed,
          playsinline: true,
          techOrder:   ["html5"],
          html5:       {
            nativeTextTracks: false,
            hls:              {
              overrideNative: true
            }
          },
          playbackRates: [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0],
          plugins:       {
            hlsQualitySelector: {}
          },
          youtube:    { ytControls: 2, start: 0 },
          controlBar: {
            children: [
              "playToggle",
              "volumePanel",
              "progressControl",
              "remainingTimeDisplay",
              "playbackRateMenuButton",
              "subsCapsButton",
              "qualitySelector",
              "fullscreenToggle"
            ]
          },
          sources: [
            {
              src:   libVideo.getHLSEncodedUrl(video),
              type:  "application/x-mpegURL",
              label: "HLS"
            }
          ],
          src: [
            {
              src:   libVideo.getHLSEncodedUrl(video),
              type:  "application/x-mpegURL",
              label: "HLS"
            }
          ]
        })
        const enableTouchActivityStub = sandbox.stub()
        const onStub = sandbox.stub()
        const hotkeysStub = sandbox.stub()
        args[2].call({
          enableTouchActivity: enableTouchActivityStub,
          on:                  onStub,
          tech_:               { hls: {} },
          hotkeys:             hotkeysStub
        })
        sinon.assert.calledWith(hotkeysStub, {
          volumeStep:                0.1,
          seekStep:                  5,
          enableModifiersForNumbers: false
        })
        sinon.assert.calledWith(enableTouchActivityStub)
        sinon.assert.calledWith(onStub)
      })
    })
  })
  ;[false, true].forEach(function(embed) {
    it("video element is rendered with the correct style attributes", () => {
      const { container } = renderPlayer({ embed })
      const videoElem = container.querySelector("video")
      assert.equal(
        videoElem.className,
        `video-js vjs-default-skin ${embed ? "video-odl-embed" : ""}`
      )
      assert.isTrue(videoElem.hasAttribute("controls"))
    })
  })

  it("video element is rendered with 4 canvas elements when multiangle", () => {
    video.multiangle = true
    const { container } = renderPlayer()
    assert.equal(container.querySelectorAll(".camera-box").length, 4)
  })

  it("video element is rendered with 1 selected canvas elements when multiangle", () => {
    video.multiangle = true
    const { container } = renderPlayer()
    assert.equal(container.querySelector(".camera-box-selected").id, "camera1")
  })

  it("selected video screen changes on click", async () => {
    const cropStub = sandbox.stub(VideoPlayerController.prototype, "cropVideo")
    video.multiangle = true
    const { container } = renderPlayer()

    fireEvent.click(container.querySelectorAll(".camera-box")[3])
    sinon.assert.calledWith(cornerFunction, "camera4")
    // clickCamera awaits cornerFunc before cropping
    await Promise.resolve()
    sinon.assert.calledOnce(cropStub)
    sinon.assert.calledWith(cropStub, Object.keys(CANVASES)[0])
  })

  it("updates subtitles on the controller when the video prop changes", () => {
    const updateStub = sandbox.stub(
      VideoPlayerController.prototype,
      "updateSubtitles"
    )
    const { rerender } = renderPlayer()
    const newVideo = {
      ...video,
      videosubtitle_set: [
        ...video.videosubtitle_set,
        makeVideoSubtitle(video.key, "fr")
      ]
    }
    rerender(
      <VideoPlayer
        video={newVideo}
        cornerFunc={cornerFunction}
        selectedCorner={Object.keys(CANVASES)[0]}
      />
    )
    sinon.assert.calledWith(updateStub, newVideo)
  })

  it("toggleFullScreen requests fullscreen when not fullscreen", () => {
    video.multiangle = true
    const { container } = renderPlayer()
    // componentDidMount hands the component's toggleFullscreen to video.js
    const videoContainer: Object = container.querySelector(".video-odl-medium")
    const requestStub = sandbox.stub()
    videoContainer.parentElement[FULLSCREEN_API.requestFullscreen] = requestStub

    libVideo.videojs.getComponent("FullscreenToggle").prototype.handleClick()

    sinon.assert.called(requestStub)
  })

  it("toggleFullScreen exits fullscreen when fullscreen", () => {
    video.multiangle = true
    renderPlayer()
    // Flow does not know the vendor-prefixed fullscreen keys FULLSCREEN_API
    // resolves to, so the stubs go on an Object-typed alias of document.
    const doc: Object = document
    const exitStub = sandbox.stub()
    try {
      // jsdom ships no fullscreen API, so FULLSCREEN_API is {} here and both
      // keys collapse to the same name -- installing the exit stub is what
      // makes isFullscreen() truthy. In a browser the two keys differ and both
      // writes matter, which is why both are set and both are cleaned up.
      doc[FULLSCREEN_API.fullscreenElement] = () => true
      doc[FULLSCREEN_API.exitFullscreen] = exitStub

      libVideo.videojs.getComponent("FullscreenToggle").prototype.handleClick()

      sinon.assert.called(exitStub)
    } finally {
      delete doc[FULLSCREEN_API.fullscreenElement]
      delete doc[FULLSCREEN_API.exitFullscreen]
    }
  })

  it("dispatches the current video time on timeupdate", () => {
    renderPlayer()
    const ready = readyPlayer()
    fireReadyEvent(ready, "loadedmetadata")
    firePlayerEvent("timeupdate")
    sinon.assert.calledWith(dispatchSpy, actions.videoUi.setVideoTime(630))
  })

  it("seeks to the start on loadedmetadata", () => {
    renderPlayer()
    const ready = readyPlayer()
    fireReadyEvent(ready, "loadedmetadata")
    sinon.assert.calledWith(ready.currentTime, 0)
  })

  describe("selectPlaylist", () => {
    describe("when elapsed time is < 10 seconds", () => {
      [1000, 2000, 3000, 4000].forEach(bandwidth => {
        it(`Returns correct playlist if bandwidth is ${bandwidth}`, () => {
          const videoTime = 5
          playerStub.tech_ = {
            currentTime: sandbox.stub().returns(videoTime),
            hls:         {
              selectPlaylist: sandbox.stub(),
              playlists:      {
                master: {
                  playlists: [
                    { attributes: { BANDWIDTH: 900 } },
                    { attributes: { BANDWIDTH: 1900 } },
                    { attributes: { BANDWIDTH: 2900 } },
                    { attributes: { BANDWIDTH: 3900 } }
                  ]
                }
              },
              systemBandwidth: bandwidth
            }
          }
          renderPlayer()
          readyPlayer()
          const bestPlayList = playerStub.tech_.hls.selectPlaylist()
          assert.equal(
            bestPlayList.attributes.BANDWIDTH,
            videoTime < 10 ? 3900 : bandwidth - 100
          )
        })
      })
    })

    describe("when elapsed time is > 10 secs", () => {
      const videoTime = 11

      it("selects highest active playlist <= system bandwidth", () => {
        playerStub.tech_ = {
          currentTime: sandbox.stub().returns(videoTime),
          hls:         {
            selectPlaylist: sandbox.stub(),
            playlists:      {
              master: {
                playlists: [
                  { attributes: { BANDWIDTH: 900 } },
                  { attributes: { BANDWIDTH: 1900 }, disabled: true },
                  { attributes: { BANDWIDTH: 2900 } },
                  { attributes: { BANDWIDTH: 3900 } }
                ]
              }
            },
            systemBandwidth: 2000
          }
        }
        renderPlayer()
        readyPlayer()
        const bestPlayList = playerStub.tech_.hls.selectPlaylist()
        assert.equal(bestPlayList.attributes.BANDWIDTH, 900)
      })

      it("selects lowest playlist if no active playlist <= system bandwidth", () => {
        playerStub.tech_ = {
          currentTime: sandbox.stub().returns(videoTime),
          hls:         {
            selectPlaylist: sandbox.stub(),
            playlists:      {
              master: {
                playlists: [
                  { attributes: { BANDWIDTH: 900 }, disabled: true },
                  { attributes: { BANDWIDTH: 1900 }, disabled: true },
                  { attributes: { BANDWIDTH: 2900 } },
                  { attributes: { BANDWIDTH: 3900 } }
                ]
              }
            },
            systemBandwidth: 2000
          }
        }
        renderPlayer()
        readyPlayer()
        const bestPlayList = playerStub.tech_.hls.selectPlaylist()
        assert.equal(bestPlayList.attributes.BANDWIDTH, 2900)
      })
    })
  })
  ;[false, true].forEach(function(isPublic) {
    ["asdJ4y", null].forEach(function(youtubeId) {
      it(`checkYouTube ${expect(
        isPublic && youtubeId !== null
      )} be called if video.is_public=${String(isPublic)} and video.youtube_id=${String(youtubeId)}`, () => {
        const images = captureImages()
        video.is_public = isPublic
        video.youtube_id = youtubeId
        video.multiangle = false
        renderPlayer()
        assert.equal(images.length, Number(isPublic && youtubeId !== null))
        if (isPublic && youtubeId !== null) {
          assert.equal(
            images[0].src,
            `https://img.youtube.com/vi/${String(youtubeId)}/0.jpg`
          )
        }
      })
    })
  })
  ;[[makeVideoSource()], []].forEach(function(sources) {
    it(`player.src() ${expect(
      sources.length > 0
    )} be called if video has ${sources.length} sources`, () => {
      const images = captureImages()
      video.is_public = true
      video.youtube_id = "asdJ4y"
      video.multiangle = false
      video.sources = sources
      renderPlayer()
      // the YouTube thumbnail failing to load is what switches the source
      images[0].onerror()
      sinon.assert.callCount(playerStub.src, sources.length > 0 ? 1 : 0)
    })
  })

  it("calls controller.resizeYouTube with the embed prop on loadedmetadata when useYouTube", () => {
    const images = captureImages()
    const resizeStub = sandbox.stub(
      VideoPlayerController.prototype,
      "resizeYouTube"
    )
    video.is_public = true
    video.youtube_id = "asdJ4y"
    video.multiangle = false
    renderPlayer({ embed: true })
    const ready = readyPlayer()
    fireReadyEvent(ready, "loadedmetadata")
    sinon.assert.calledWith(resizeStub, true)
    // sanity: the useYouTube path really ran (checkYouTube's thumbnail check)
    assert.equal(images.length, 1)
  })
})
