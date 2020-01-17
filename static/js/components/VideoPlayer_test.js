// @flow
/* global SETTINGS */
import React from "react"
import { Provider } from "react-redux"
import { assert } from "chai"
import sinon from "sinon"
import { mount } from "enzyme"
import { URLSearchParams } from "url"
import VideoPlayer from "./VideoPlayer"
import {
  makeVideo,
  makeVideoSource,
  makeVideoSubtitle
} from "../factories/video"
import * as libVideo from "../lib/video"
import ga from "react-ga"
import { FULLSCREEN_API } from "../util/fullscreen_api"
import { CANVASES } from "../constants"
import { makeVideoSubtitleUrl } from "../lib/urls"
import { expect } from "../util/test_utils"
import configureTestStore from "redux-asserts"
import rootReducer from "../reducers"

global.URLSearchParams = URLSearchParams

describe("VideoPlayer", () => {
  let video,
    videojsStub,
    sandbox,
    cornerFunction,
    playerStub,
    containerStub,
    nodeStub,
    gaEventStub,
    gaSetStub,
    store

  const renderPlayer = (props = {}) =>
    mount(
      <Provider store={store}>
        <VideoPlayer
          video={video}
          cornerFunc={cornerFunction}
          selectedCorner={Object.keys(CANVASES)[0]}
          {...props}
        />
      </Provider>
    )

  beforeEach(() => {
    video = makeVideo()
    sandbox = sinon.sandbox.create()
    cornerFunction = sandbox.stub()
    gaEventStub = sandbox.stub(ga, "event")
    gaSetStub = sandbox.stub(ga, "set")
    playerStub = {
      el_: {
        style:         {},
        dispatchEvent: sandbox.stub()
      },
      tracks:        [],
      on:            sandbox.stub(),
      tech_:         {},
      reset:         sandbox.stub().returns(playerStub),
      src:           sandbox.stub().returns(playerStub),
      fluid:         sandbox.stub().returns(playerStub),
      width:         sandbox.stub(),
      height:        sandbox.stub(),
      currentTime:   () => 630.5,
      duration:      () => 2400.0,
      videoWidth:    () => 640,
      videoHeight:   () => 360,
      currentWidth:  () => 1280,
      currentHeight: () => 720,
      textTracks:    function() {
        return this.tracks
      },
      removeRemoteTextTrack: function(track) {
        this.tracks.splice(this.tracks.indexOf(track), 1)
      },
      addRemoteTextTrack: function(track) {
        this.tracks.push({ src: track.src, addEventListener: function() {} })
      }
    }
    containerStub = { style: {}, parentElement: { style: {} } }
    nodeStub = { style: {} }
    videojsStub = sandbox.stub(libVideo, "videojs").returns(playerStub)
    store = configureTestStore(rootReducer)
  })

  afterEach(() => {
    sandbox.restore()
  })
  ;[true, false].forEach(function(embed) {
    [true, false].forEach(function(multiangle) {
      it("uses videojs on mount with the right arguments", () => {
        SETTINGS.ga_dimension_camera = "dimension1"
        video.multiangle = multiangle
        renderPlayer({ embed })
        sinon.assert.called(videojsStub)
        const args = videojsStub.firstCall.args
        assert.equal(args[0].tagName, "VIDEO")
        assert.deepEqual(args[1], {
          autoplay:    false,
          controls:    true,
          fluid:       embed,
          playsinline: true,
          techOrder:   ["html5"],
          html5:       {
            nativeTextTracks: false
          },
          playbackRates: [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0],
          plugins:       {
            hlsQualitySelector: {}
          },
          youtube:    { ytControls: 2 },
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
        args[2].call({
          enableTouchActivity: enableTouchActivityStub,
          on:                  onStub,
          tech_:               { hls: {} }
        })
        sinon.assert.calledWith(enableTouchActivityStub)
        sinon.assert.calledWith(onStub)
        if (video.multiangle) {
          sinon.assert.calledWith(gaSetStub, {
            dimension1: "camera1"
          })
        } else {
          sinon.assert.notCalled(gaSetStub)
        }
      })
    })
  })
  ;[false, true].forEach(function(embed) {
    it("video element is rendered with the correct style attributes", () => {
      const wrapper = renderPlayer({ embed }).find("VideoPlayer")
      const videoProps = wrapper.find("video").props()
      assert.equal(
        videoProps.className,
        `video-js vjs-default-skin ${embed ? "video-odl-embed" : ""}`
      )
      assert(videoProps.controls !== undefined)
    })
  })

  it("video element is rendered with 4 canvas elements when multiangle", () => {
    video.multiangle = true
    const wrapper = renderPlayer().find("VideoPlayer")
    const canvases = wrapper.find(".camera-box")
    assert.equal(canvases.length, 4)
  })

  it("video element is rendered with 1 selected canvas elements when multiangle", () => {
    video.multiangle = true
    const wrapper = renderPlayer().find("VideoPlayer")
    const canvas = wrapper.find(".camera-box-selected").at(0)
    assert.equal(canvas.props().id, "camera1")
  })

  it("selected video screen changes on click", () => {
    SETTINGS.ga_dimension_camera = "dimension1"
    video.multiangle = true
    const wrapper = renderPlayer().find("VideoPlayer")

    const canvases = wrapper.find(".camera-box")
    canvases.at(3).prop("onClick")()
    sinon.assert.calledWith(cornerFunction, "camera4")
    sinon.assert.calledWith(gaSetStub, {
      dimension1: "camera4"
    })
    sinon.assert.calledWith(gaEventStub, {
      category: "video",
      action:   "changeCameraView",
      label:    video.key,
      value:    631
    })
  })

  it("cropVideo modifies style and configureCameras function called", () => {
    video.multiangle = true
    sandbox.stub(window, "getComputedStyle").returns({ maxHeight: 600 })
    const wrapper = renderPlayer().find("VideoPlayer")
    wrapper.instance().player = playerStub
    wrapper.instance().videoNode = nodeStub
    wrapper.instance().videoContainer = containerStub
    wrapper.instance().cropVideo()
    assert.deepEqual(wrapper.instance().videoNode.style, {
      left:      "640px",
      top:       "360px",
      transform: "scale(2)"
    })
  })
  ;[1000, 4000].forEach(function(videoWidth) {
    it("resizeYoutube modifies the video width and height", () => {
      const wrapper = renderPlayer().find("VideoPlayer")
      sandbox.stub(window, "getComputedStyle").returns({ maxHeight: "700px" })
      containerStub = {
        style:         {},
        parentElement: { style: {} },
        clientWidth:   videoWidth
      }
      wrapper.instance().player = playerStub
      wrapper.instance().videoNode = nodeStub
      wrapper.instance().videoContainer = containerStub
      wrapper.instance().resizeYouTube()
      sinon.assert.calledWith(
        wrapper.instance().player.width,
        wrapper.instance().videoContainer.clientWidth
      )
      sinon.assert.calledWith(
        wrapper.instance().player.height,
        Math.min(videoWidth / wrapper.instance().aspectRatio, 700)
      )
    })
  })

  it("drawCanvas calls inner drawCanvasImage", () => {
    video.multiangle = true
    sandbox.stub(window, "getComputedStyle").returns({ maxHeight: 600 })
    const wrapper = renderPlayer().find("VideoPlayer")
    wrapper.instance().player = playerStub
    wrapper.instance().videoNode = nodeStub
    const canvas = wrapper.find(".camera-box").at(0)
    assert.throws(
      () => wrapper.instance().drawCanvas(canvas, true, false),
      TypeError,
      "getContext"
    )
  })

  it("subtitles added to and removed from player", () => {
    const captionToKeep = video.videosubtitle_set[0]
    const captionToDelete = makeVideoSubtitle(video.key, "es")
    const captionToAdd = makeVideoSubtitle(video.key, "fr")
    video.videosubtitle_set.push(captionToDelete)
    const wrapper = renderPlayer().find("VideoPlayer")
    wrapper.instance().player = playerStub
    wrapper.instance().updateSubtitles()
    assert.equal(wrapper.instance().player.tracks.length, 2)
    assert.equal(
      wrapper.instance().player.tracks[0].src,
      makeVideoSubtitleUrl(captionToKeep)
    )
    assert.equal(
      wrapper.instance().player.tracks[1].src,
      makeVideoSubtitleUrl(captionToDelete)
    )
    video.videosubtitle_set = [captionToKeep, captionToAdd]
    wrapper.instance().updateSubtitles()
    assert.equal(wrapper.instance().player.tracks.length, 2)
    assert.equal(
      wrapper.instance().player.tracks[0].src,
      makeVideoSubtitleUrl(captionToKeep)
    )
    assert.equal(
      wrapper.instance().player.tracks[1].src,
      makeVideoSubtitleUrl(captionToAdd)
    )
  })

  it("has a playback speed button on the control bar", () => {
    const wrapper = renderPlayer().find("VideoPlayer")
    assert.isDefined(wrapper.find(".vjs-playback-rate-value"))
  })

  it("toggleFullScreen on causes player to dispatchEvent", () => {
    const wrapper = renderPlayer().find("VideoPlayer")
    wrapper.instance().player = playerStub
    // $FlowFixMe
    containerStub.parentElement[FULLSCREEN_API.requestFullscreen] = () => {}
    wrapper.instance().videoContainer = containerStub

    wrapper.instance().toggleFullscreen()
    sinon.assert.calledWith(
      wrapper.instance().player.el_.dispatchEvent,
      new Event("fullscreen on")
    )
  })

  it("toggleFullScreen off causes player to dispatchEvent", () => {
    const wrapper = renderPlayer().find("VideoPlayer")
    wrapper.instance().player = playerStub
    // $FlowFixMe
    document[FULLSCREEN_API.fullscreenElement] = () => {
      return true
    }
    wrapper.instance().videoContainer = containerStub

    wrapper.instance().toggleFullscreen()
    sinon.assert.calledWith(
      wrapper.instance().player.el_.dispatchEvent,
      new Event("fullscreen off")
    )
  })
  ;[
    "play",
    "pause",
    "seeked",
    "timeupdate",
    "changeCameraView",
    "fullscreen off",
    "fullscreen on",
    "ended"
  ].forEach(event => {
    it(`sets up GA trigger for player event ${event}`, () => {
      const wrapper = renderPlayer().find("VideoPlayer")
      wrapper.instance().player = playerStub
      wrapper.instance().createEventHandler(event, event)
      assert.isTrue(wrapper.instance().player.on.calledWith(event))
    })

    it(`sends the correct event to google analytics for ${event}`, () => {
      const wrapper = renderPlayer().find("VideoPlayer")
      wrapper.instance().player = playerStub
      wrapper.instance().lastMinuteTracked = -1
      wrapper.instance().sendEvent(event, video.key)
      if (event !== "timeupdate") {
        sinon.assert.calledWith(gaEventStub, {
          category: "video",
          action:   event,
          label:    video.key,
          value:    631
        })
      } else {
        sinon.assert.calledWith(gaEventStub, {
          category: "video",
          action:   "T0010",
          label:    video.key,
          value:    1
        })
      }
    })
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
          const wrapper = renderPlayer().find("VideoPlayer")
          wrapper.instance().player = playerStub
          const bestPlayList = wrapper.instance().selectPlaylist()
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
        const wrapper = renderPlayer().find("VideoPlayer")
        wrapper.instance().player = playerStub
        const bestPlayList = wrapper.instance().selectPlaylist()
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
        const wrapper = renderPlayer().find("VideoPlayer")
        wrapper.instance().player = playerStub
        const bestPlayList = wrapper.instance().selectPlaylist()
        assert.equal(bestPlayList.attributes.BANDWIDTH, 2900)
      })
    })
  })
  ;[false, true].forEach(function(isPublic) {
    ["asdJ4y", null].forEach(function(youtubeId) {
      it(`checkYouTube ${expect(
        isPublic && youtubeId !== null
      )} be called if video.is_public=${String(isPublic)} and video.youtube_id=${String(youtubeId)}`, async () => {
        video.is_public = isPublic
        video.youtube_id = youtubeId
        video.multiangle = false
        const wrapper = renderPlayer().find("VideoPlayer")
        const checkStub = sandbox.stub(wrapper.instance(), "checkYouTube")
        wrapper.instance().componentDidMount()
        sinon.assert.callCount(
          checkStub,
          Number(isPublic && youtubeId !== null)
        )
      })
    })
  })
  ;[[makeVideoSource()], []].forEach(function(sources) {
    it(`player.reset() ${expect(
      sources.length > 0
    )} be called if video has ${sources.length} sources`, async () => {
      video.sources = sources
      sandbox.stub(window, "Image")
      const wrapper = await renderPlayer().find("VideoPlayer")
      wrapper.instance().switchVideoSource()
      sinon.assert.callCount(
        wrapper.instance().player.reset,
        sources.length > 0 ? 1 : 0
      )
    })
  })

  it("renders overlayChildren", () => {
    const overlayChildKeys = [...Array(3).keys()].map(i => `child-${i}`)
    const overlayChildren = overlayChildKeys.map(key => {
      return <div key={key} className="overlay-child" />
    })
    const wrapper = renderPlayer({ overlayChildren })
    const renderedChildKeys = wrapper.find(".overlay-child").map(el => el.key())
    assert.deepEqual(overlayChildKeys.sort(), renderedChildKeys.sort())
  })
})
