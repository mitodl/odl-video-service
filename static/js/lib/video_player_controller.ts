import { makeVideoSubtitleUrl } from "./urls"
import type { Video, VideoSubtitle } from "../types/videoTypes"
import { FULLSCREEN_API } from "../util/fullscreen_api"
import { CANVASES } from "../constants"
import { sendGAEvent } from "../util/google_analytics"

/*
 * The slice of the video.js player API this controller drives. video.js ships
 * its own types, but they describe neither `el_` (a private the component and
 * this module both reach for) nor the `src` the text tracks carry, and the
 * tests hand the controller a plain stub rather than a real player. A
 * structural type keeps both callers honest without dragging in the whole
 * Player class.
 */
type PlayerTextTrack = {
  src: string
  addEventListener: (type: string, listener: () => void) => void
}

export type VideoJsPlayer = {
  el_: { style: { [key: string]: string } }
  currentTime: () => number
  currentWidth: () => number
  currentHeight: () => number
  videoWidth: () => number
  videoHeight: () => number
  width: (width: number) => void
  height: (height: number) => void
  textTracks: () => ArrayLike<PlayerTextTrack>
  addRemoteTextTrack: (
    options: {
      kind: string
      src: string
      srcLang: string
      label: string
    },
    manualCleanup: boolean
  ) => void
  removeRemoteTextTrack: (track: PlayerTextTrack) => void
}

export const isFullscreen = () => {
  return document[FULLSCREEN_API.fullscreenElement]
}

const drawCanvasImage = function(
  canvas: HTMLCanvasElement,
  videoNode: HTMLVideoElement,
  shiftX: boolean,
  shiftY: boolean
) {
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
  player: VideoJsPlayer | null
  videoNode: HTMLVideoElement | null
  videoContainer: HTMLDivElement | null
  cameras: HTMLDivElement | null
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
      // make the typechecker happy
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
      // Each canvas is looked up by the camera name it carries as an id --
      // HTMLCollection's named access, which its type does not describe: the
      // declaration only covers the numeric indexing.
      const canvasElements = this.cameras.getElementsByTagName(
        "canvas"
      ) as unknown as { [key: string]: HTMLCanvasElement }
      Object.keys(CANVASES).forEach(corner => {
        const canvasName = corner as keyof typeof CANVASES
        this.drawCanvas(
          canvasElements[canvasName],
          CANVASES[canvasName].shiftX,
          CANVASES[canvasName].shiftY
        )
      })
    }
  }

  resizeYouTube(embed: boolean | null) {
    if (!isFullscreen() && !embed) {
      if (!this.aspectRatio) {
        this.aspectRatio =
          this.player.currentWidth() / this.player.currentHeight()
      }
      // resizeYouTube only runs from player callbacks registered in
      // onPlayerReady, by which point render() has set videoContainer.
      const maxWidth = this.videoContainer.clientWidth
      this.player.width(maxWidth)
      const maxHeight = window
        .getComputedStyle(this.videoContainer)
        .maxHeight.replace("px", "")
      // Math.min coerced this string to a number on its own; Number() makes
      // the identical conversion explicit for the typechecker.
      this.player.height(
        Math.min(Number(maxHeight), maxWidth / this.aspectRatio)
      )
    }
  }

  cropVideo(selectedCorner: string) {
    const corner = selectedCorner as keyof typeof CANVASES
    const shiftX = CANVASES[corner].shiftX
    const shiftY = CANVASES[corner].shiftY
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
      // Make the typechecker happy
      throw new Error("Missing videoContainer")
    }
    this.videoContainer.style.maxWidth = `${videoWidth}px`
    // videoContainer is the .video-odl-medium div, which render() always
    // emits inside .video-odl-center, so parentElement is never null.
    this.videoContainer.parentElement.style.width = `${
      videoWidth + canvasWidth
    }px`
    const left = Math.round(this.player.currentWidth() / (shiftX ? -2 : 2))
    const top = Math.round(this.player.currentHeight() / (shiftY ? -2 : 2))

    if (!this.videoNode) {
      // Make the typechecker happy
      throw new Error("Missing videoNode")
    }

    this.videoNode.style.left = `${left}px`
    this.videoNode.style.top = `${top}px`
    // prop is a vendor-prefixed transform name, not a declared CSSStyleDeclaration key
    this.videoNode.style[prop] = "scale(2)"
    this.configureCameras()
  }
}
