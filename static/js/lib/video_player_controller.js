// @flow
/* global SETTINGS: false */
import { makeVideoSubtitleUrl } from "./urls"
import type { Video, VideoSubtitle } from "../flow/videoTypes"
import { FULLSCREEN_API } from "../util/fullscreen_api"
import { CANVASES } from "../constants"
import { sendGAEvent } from "../util/google_analytics"

export const isFullscreen = () => {
  // $FlowFixMe
  return document[FULLSCREEN_API.fullscreenElement]
}

const drawCanvasImage = function(canvas, videoNode, shiftX, shiftY) {
  const x = shiftX ? Math.floor(videoNode.videoWidth / 2) : 0
  const y = shiftY ? Math.floor(videoNode.videoHeight / 2) : 0
  const context = canvas.getContext("2d")
  context.drawImage(
    videoNode,
    x,
    y,
    Math.floor(videoNode.videoWidth / 2),
    Math.floor(videoNode.videoHeight / 2),
    0,
    0,
    canvas.width,
    canvas.height
  )
  setTimeout(drawCanvasImage, 20, canvas, videoNode, shiftX, shiftY)
}

/*
 * The imperative video.js glue extracted from the VideoPlayer component
 * (mitodl/hq#12639). Holds the DOM/player refs the component assigns and
 * owns every geometry/subtitle operation on them, so it can be unit-tested
 * with plain stubs and no renderer.
 */
export class VideoPlayerController {
  player: ?Object
  videoNode: ?HTMLVideoElement
  videoContainer: ?HTMLDivElement
  cameras: ?HTMLDivElement
  aspectRatio: number

  updateSubtitles(video: Video) {
    if (this.player) {
      // Remove existing tracks for deleted subtitles
      const tracks = this.player.textTracks()
      const subtitleUrls = video.videosubtitle_set.map(
        (subtitle: VideoSubtitle) => makeVideoSubtitleUrl(subtitle)
      )
      const trackUrls = []
      for (let idx = 0; idx < tracks.length; idx++) {
        if (tracks[idx] && !subtitleUrls.includes(tracks[idx].src)) {
          this.player.removeRemoteTextTrack(tracks[idx])
        } else {
          trackUrls.push(tracks[idx].src)
        }
      }
      // Add tracks for any new subtitles associated with the video
      video.videosubtitle_set.forEach((subtitle: VideoSubtitle) => {
        const subUrl = makeVideoSubtitleUrl(subtitle)
        if (!trackUrls.includes(subUrl)) {
          this.player.addRemoteTextTrack(
            {
              kind:    "captions",
              src:     subUrl,
              srcLang: subtitle.language,
              label:   subtitle.language_name
            },
            true
          )
        }
        // Add listeners to each track
        const player = this.player
        for (let idx = 0; idx < this.player.textTracks().length; idx++) {
          if (!trackUrls.includes(tracks[idx].src)) {
            tracks[idx].addEventListener("modechange", function() {
              sendGAEvent(
                "video",
                `Subtitles ${this.label} ${this.mode}`,
                video.key,
                player.currentTime()
              )
            })
          }
        }
      })
    }
  }

  drawCanvas(canvas: HTMLCanvasElement, shiftX: boolean, shiftY: boolean) {
    if (!this.videoNode) {
      // make flow happy
      throw new Error("Missing videoNode")
    }
    const { offsetWidth, offsetHeight } = this.videoNode
    canvas.width = Math.floor(offsetWidth / 4) - 2
    canvas.height = Math.floor(offsetHeight / 4) - 2
    if (canvas && this.videoNode) {
      drawCanvasImage(canvas, this.videoNode, shiftX, shiftY)
    }
  }

  configureCameras() {
    if (this.cameras) {
      const canvasElements = this.cameras.getElementsByTagName("canvas")
      Object.keys(CANVASES).forEach(corner => {
        this.drawCanvas(
          // $FlowFixMe - corner does not have to be a number
          canvasElements[corner],
          CANVASES[corner].shiftX,
          CANVASES[corner].shiftY
        )
      })
    }
  }

  resizeYouTube(embed: ?boolean) {
    if (!isFullscreen() && !embed) {
      if (!this.aspectRatio) {
        this.aspectRatio =
          this.player.currentWidth() / this.player.currentHeight()
      }
      // resizeYouTube only runs from player callbacks registered in
      // onPlayerReady, by which point render() has set videoContainer.
      // $FlowFixMe Flow cannot narrow the ref across that indirection
      const maxWidth = this.videoContainer.clientWidth
      this.player.width(maxWidth)
      const maxHeight = window
        .getComputedStyle(this.videoContainer)
        .maxHeight.replace("px", "")
      this.player.height(Math.min(maxHeight, maxWidth / this.aspectRatio))
    }
  }

  cropVideo(selectedCorner: string) {
    const shiftX = CANVASES[selectedCorner].shiftX
    const shiftY = CANVASES[selectedCorner].shiftY
    const transformProps = [
      "transform",
      "WebkitTransform",
      "MozTransform",
      "msTransform",
      "OTransform"
    ]

    const prop =
      transformProps.find(
        property => this.player.el_.style[property] !== undefined
      ) || transformProps[0]
    const aspectRatio = this.player.videoWidth() / this.player.videoHeight()
    let videoWidth = Math.min(
      parseInt(window.getComputedStyle(this.videoNode).maxHeight) * aspectRatio,
      window.innerWidth,
      screen.width
    )
    if (isNaN(videoWidth) || isFullscreen()) {
      videoWidth = Math.min(window.innerWidth, screen.width)
    }
    const canvasWidth = Math.floor(videoWidth / 4)
    videoWidth = Math.floor(
      videoWidth - (canvasWidth - canvasWidth / aspectRatio / 3)
    )

    if (!this.videoContainer) {
      // Make flow happy
      throw new Error("Missing videoContainer")
    }
    this.videoContainer.style.maxWidth = `${videoWidth}px`
    // videoContainer is the .video-odl-medium div, which render() always
    // emits inside .video-odl-center, so parentElement is never null.
    // $FlowFixMe Flow cannot prove that from the ref's type
    this.videoContainer.parentElement.style.width = `${videoWidth +
      canvasWidth}px`
    const left = Math.round(this.player.currentWidth() / (shiftX ? -2 : 2))
    const top = Math.round(this.player.currentHeight() / (shiftY ? -2 : 2))

    if (!this.videoNode) {
      // Make flow happy
      throw new Error("Missing videoNode")
    }

    this.videoNode.style.left = `${left}px`
    this.videoNode.style.top = `${top}px`
    // $FlowFixMe prop does not have to be a number
    this.videoNode.style[prop] = "scale(2)"
    this.configureCameras()
  }
}
