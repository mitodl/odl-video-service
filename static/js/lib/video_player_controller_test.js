// @flow
/* global SETTINGS */
import { assert } from "chai"
import sinon from "sinon"
import ga from "react-ga"
import { VideoPlayerController, isFullscreen } from "./video_player_controller"
import { makeVideo, makeVideoSubtitle } from "../factories/video"
import { makeVideoSubtitleUrl } from "./urls"
import { FULLSCREEN_API } from "../util/fullscreen_api"
import { CANVASES } from "../constants"
import { makePlayerStub } from "../testUtils/playerStub"

describe("VideoPlayerController", () => {
  let sandbox,
    controller,
    video,
    playerStub,
    containerStub,
    nodeStub,
    gaEventStub

  beforeEach(() => {
    video = makeVideo()
    sandbox = sinon.createSandbox()
    sandbox.stub(global, "setTimeout")
    gaEventStub = sandbox.stub(ga, "event")
    playerStub = makePlayerStub(sandbox)
    containerStub = { style: {}, parentElement: { style: {} } }
    nodeStub = { style: {} }
    // The refs VideoPlayer's render() and componentDidMount assign. Tests
    // that care about a specific shape override the one ref they exercise.
    controller = new VideoPlayerController()
    controller.player = playerStub
    controller.videoNode = nodeStub
    controller.videoContainer = containerStub
  })

  afterEach(() => {
    sandbox.restore()
  })

  it("cropVideo modifies style and calls configureCameras", () => {
    sandbox.stub(window, "getComputedStyle").returns({ maxHeight: 600 })
    const configureStub = sandbox.stub(controller, "configureCameras")
    controller.cropVideo(Object.keys(CANVASES)[0])
    assert.deepEqual(controller.videoNode.style, {
      left:      "640px",
      top:       "360px",
      transform: "scale(2)"
    })
    sinon.assert.calledOnce(configureStub)
  })
  ;[1000, 4000].forEach(function(videoWidth) {
    it(`resizeYouTube modifies the video width and height (container ${videoWidth})`, () => {
      sandbox.stub(window, "getComputedStyle").returns({ maxHeight: "700px" })
      controller.videoContainer = {
        style:         {},
        parentElement: { style: {} },
        clientWidth:   videoWidth
      }
      controller.resizeYouTube(false)
      sinon.assert.calledWith(playerStub.width, videoWidth)
      sinon.assert.calledWith(
        playerStub.height,
        Math.min(videoWidth / controller.aspectRatio, 700)
      )
    })
  })

  it("resizeYouTube does nothing when embedded", () => {
    controller.resizeYouTube(true)
    sinon.assert.notCalled(playerStub.width)
    sinon.assert.notCalled(playerStub.height)
  })

  it("resizeYouTube does nothing in fullscreen", () => {
    document[FULLSCREEN_API.fullscreenElement] = () => true
    try {
      controller.resizeYouTube(false)
    } finally {
      delete document[FULLSCREEN_API.fullscreenElement]
    }
    sinon.assert.notCalled(playerStub.width)
    sinon.assert.notCalled(playerStub.height)
  })

  it("drawCanvas throws without a real canvas", () => {
    controller.videoNode = { offsetWidth: 402, offsetHeight: 202 }
    assert.throws(
      () => controller.drawCanvas(({}: any), true, false),
      TypeError,
      "getContext"
    )
  })
  ;[
    [false, false],
    [true, false],
    [false, true],
    [true, true]
  ].forEach(([shiftX, shiftY]) => {
    it(`drawCanvas sizes and crops the canvas (shiftX=${String(
      shiftX
    )}, shiftY=${String(shiftY)})`, () => {
      const context = { drawImage: sandbox.stub() }
      const canvas = { getContext: sandbox.stub().returns(context) }
      const videoNode = {
        offsetWidth:  402,
        offsetHeight: 202,
        videoWidth:   640,
        videoHeight:  360
      }
      controller.videoNode = videoNode
      controller.drawCanvas((canvas: any), shiftX, shiftY)
      assert.equal(canvas.width, 98)
      assert.equal(canvas.height, 48)
      sinon.assert.calledWith(
        context.drawImage,
        videoNode,
        shiftX ? 320 : 0,
        shiftY ? 180 : 0,
        320,
        180,
        0,
        0,
        98,
        48
      )
      sinon.assert.called(global.setTimeout)
    })
  })

  it("configureCameras draws one canvas per corner", () => {
    const canvasElements = {}
    Object.keys(CANVASES).forEach(corner => {
      canvasElements[corner] = { id: corner }
    })
    controller.cameras = ({
      getElementsByTagName: sandbox.stub().returns(canvasElements)
    }: any)
    const drawStub = sandbox.stub(controller, "drawCanvas")
    controller.configureCameras()
    Object.keys(CANVASES).forEach(corner => {
      sinon.assert.calledWith(
        drawStub,
        canvasElements[corner],
        CANVASES[corner].shiftX,
        CANVASES[corner].shiftY
      )
    })
  })

  it("subtitles added to and removed from player", () => {
    const captionToKeep = video.videosubtitle_set[0]
    const captionToDelete = makeVideoSubtitle(video.key, "es")
    const captionToAdd = makeVideoSubtitle(video.key, "fr")
    video.videosubtitle_set.push(captionToDelete)
    controller.updateSubtitles(video)
    assert.equal(playerStub.tracks.length, 2)
    assert.equal(playerStub.tracks[0].src, makeVideoSubtitleUrl(captionToKeep))
    assert.equal(
      playerStub.tracks[1].src,
      makeVideoSubtitleUrl(captionToDelete)
    )
    video.videosubtitle_set = [captionToKeep, captionToAdd]
    controller.updateSubtitles(video)
    assert.equal(playerStub.tracks.length, 2)
    assert.equal(playerStub.tracks[0].src, makeVideoSubtitleUrl(captionToKeep))
    assert.equal(playerStub.tracks[1].src, makeVideoSubtitleUrl(captionToAdd))
  })

  it("updateSubtitles sends a GA event when a track's mode changes", () => {
    controller.updateSubtitles(video)
    const track = playerStub.tracks[0]
    const call = track.addEventListener
      .getCalls()
      .find(c => c.args[0] === "modechange")
    assert.isOk(call)
    call.args[1].call({ label: "English", mode: "showing" })
    sinon.assert.calledWith(gaEventStub, {
      category: "video",
      action:   "Subtitles English showing",
      label:    video.key,
      value:    631
    })
  })

  it("updateSubtitles does nothing without a player", () => {
    // videojs() has not returned yet, so componentDidMount has not assigned
    // the player -- a componentDidUpdate in that window must be a no-op.
    controller.player = null
    controller.updateSubtitles(video)
    assert.equal(playerStub.tracks.length, 0)
  })

  it("isFullscreen reflects the document fullscreen element", () => {
    assert.isNotOk(isFullscreen())
    document[FULLSCREEN_API.fullscreenElement] = () => true
    try {
      assert.isOk(isFullscreen())
    } finally {
      delete document[FULLSCREEN_API.fullscreenElement]
    }
  })
})
