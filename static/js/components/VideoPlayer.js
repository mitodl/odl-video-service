// @flow
/* global videojs: true */
/* global SETTINGS: false */
import React from "react"
import R from "ramda"
import _ from "lodash"
import type { Dispatch } from "redux"
import { makeVideoSubtitleUrl } from "../lib/urls"
import { videojs } from "../lib/video"
import type { Video, VideoSubtitle } from "../flow/videoTypes"
import { FULLSCREEN_API } from "../util/fullscreen_api"
import { CANVASES } from "../constants"
import { sendGAEvent, setCustomDimension } from "../util/google_analytics"
import { actions } from "../actions"
import { connect } from "react-redux"

const gaEvents = [
  "play",
  "pause",
  "seeked",
  "timeupdate",
  "fullscreen off",
  "fullscreen on",
  "ended"
]

const makeConfigForVideo = (
  video: Video,
  useYouTube: boolean,
  embedded: ?boolean,
  startTime: number
): Object => ({
  autoplay:    false,
  controls:    true,
  fluid:       embedded || false,
  playsinline: true,
  techOrder:   useYouTube ? ["youtube", "html5"] : ["html5"],
  html5:       {
    nativeTextTracks: false
  },
  playbackRates: [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0],
  sources:       useYouTube
    ? [
      {
        type: "video/youtube",
        src:  `https://www.youtube.com/watch?v=${video.youtube_id || ""}`
      }
    ]
    : video.sources,
  src:     video.sources,
  youtube: { ytControls: 2, start: startTime },
  plugins: {
    hlsQualitySelector: {}
  },
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
  }
})

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

const isFullscreen = function() {
  // $FlowFixMe
  return document[FULLSCREEN_API.fullscreenElement]
}

class VideoPlayer extends React.Component<*, void> {
  props: {
    dispatch: Dispatch,
    video: Video,
    selectedCorner: string,
    cornerFunc: (corner: string) => void,
    embed: ?boolean,
    videoPlayerRef?: (player: any) => void,
    overlayChildren?: any
  }

  player: Object
  videoNode: ?HTMLVideoElement
  videoContainer: ?HTMLDivElement
  cameras: ?HTMLDivElement
  lastMinuteTracked: ?number
  aspectRatio: number

  updateSubtitles() {
    const { video } = this.props
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

  resizeYouTube = () => {
    const { embed } = this.props
    if (!isFullscreen() && !embed) {
      if (!this.aspectRatio) {
        this.aspectRatio =
          this.player.currentWidth() / this.player.currentHeight()
      }
      // $FlowFixMe videoContainer is not going to be null
      const maxWidth = this.videoContainer.clientWidth
      this.player.width(maxWidth)
      const maxHeight = window
        .getComputedStyle(this.videoContainer)
        .maxHeight.replace("px", "")
      this.player.height(Math.min(maxHeight, maxWidth / this.aspectRatio))
    }
  }

  cropVideo = () => {
    const { selectedCorner } = this.props
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
    // $FlowFixMe videoContainer.parentElement is not going to be null
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

  toggleFullscreen = () => {
    const fullscreen = isFullscreen()
    if (fullscreen) {
      // $FlowFixMe
      document[FULLSCREEN_API.exitFullscreen]()
    } else {
      // $FlowFixMe videoContainer.parentElement is not going to be null
      this.videoContainer.parentElement[FULLSCREEN_API.requestFullscreen]()
    }
    this.player.el_.dispatchEvent(
      new Event(`fullscreen ${fullscreen ? "off" : "on"}`)
    )
  }

  switchVideoSource = () => {
    const { video } = this.props
    if (video.sources.length > 0) {
      this.player.reset().src(video.sources)
    }
  }

  imageExists(url: string) {
    const img = new Image()
    img.onerror = this.switchVideoSource
    img.src = url
  }

  checkYouTube = async () => {
    const { video } = this.props
    // Try to load the YouTube video thumbnail image.  Assumes video availability == thumbnail availability
    const imgUrl = `https://img.youtube.com/vi/${video.youtube_id || ""}/0.jpg`
    this.imageExists(imgUrl)
  }

  sendEvent = (action: string, label: string) => {
    const { dispatch } = this.props
    if (action === "timeupdate") {
      // Track amount played in increments of 60 seconds
      const currentTime = this.player.currentTime()
      const nearestMinute = parseInt((currentTime - currentTime % 60) / 60)
      if (this.lastMinuteTracked !== nearestMinute) {
        sendGAEvent(
          "video",
          "T".concat(nearestMinute.toString().padStart(4, "0")),
          label,
          1
        )
        this.lastMinuteTracked = nearestMinute
      }
      dispatch(actions.videoUi.setVideoTime(Math.floor(currentTime)))
    } else {
      sendGAEvent("video", action, label, this.player.currentTime())
    }
  }

  createEventHandler = (action: string, label: string) => {
    const sendEvent = this.sendEvent
    this.player.on(action, function() {
      sendEvent(action, label)
    })
  }

  selectPlaylist = () => {
    const sortByBandwidth = R.sortBy(R.path(["attributes", "BANDWIDTH"]))
    const playlists = sortByBandwidth(
      this.player.tech_.hls.playlists.master.playlists
    )
    // Always start with highest bandwidth for first 10 seconds
    if (this.player.tech_.currentTime() < 10) {
      return _.last(playlists)
    }
    // Return active playlist with highest bandwidth <= system bandwidth,
    // or first active playlist otherwise.
    const activePlaylists = R.filter(rep => !rep.disabled, playlists)
    return (
      _.last(
        R.filter(rep => {
          return (
            rep.attributes.BANDWIDTH <=
            _.max([
              this.player.tech_.hls.systemBandwidth,
              playlists[0].attributes.BANDWIDTH
            ])
          )
        }, activePlaylists)
      ) || activePlaylists[0]
    )
  }

  componentDidMount() {
    const { video, selectedCorner, embed, videoPlayerRef } = this.props
    if (videoPlayerRef) {
      videoPlayerRef(this)
    }
    const cropVideo = this.cropVideo
    const resizeYouTube = this.resizeYouTube
    const createEventHandler = this.createEventHandler
    const toggleFullscreen = this.toggleFullscreen
    if (video.multiangle) {
      videojs.getComponent(
        "FullscreenToggle"
      ).prototype.handleClick = toggleFullscreen
    }
    const useYouTube = video.is_public && video.youtube_id !== null
    this.lastMinuteTracked = null
    const selectPlaylist = this.selectPlaylist.bind(this)
    const self = this
    const params = new URLSearchParams(window.location.search)
    const startTime = parseInt(params.get("start")) || 0
    this.player = videojs(
      this.videoNode,
      makeConfigForVideo(video, useYouTube, embed, startTime),
      function onPlayerReady() {
        this.enableTouchActivity()
        if (video.multiangle) {
          setCustomDimension(SETTINGS.ga_dimension_camera, selectedCorner)
          this.on("loadeddata", cropVideo)
          this.on(FULLSCREEN_API.fullscreenchange, cropVideo)
          window.addEventListener("resize", cropVideo)
        } else if (useYouTube) {
          this.on("loadedmetadata", resizeYouTube)
          window.addEventListener("resize", resizeYouTube)
        }
        this.on("onLoadedMetadata", function() {
          self.props.dispatch(
            actions.videoUi.setVideoDuration(self.player.duration())
          )
          gaEvents.forEach((event: string) => {
            createEventHandler(event, video.key)
          })
          if (!useYouTube) {
            this.currentTime(startTime)
          }
        })
        if (this.tech_.hls !== undefined) {
          this.tech_.hls.selectPlaylist = selectPlaylist
        }
      }
    )
    if (useYouTube) {
      this.checkYouTube()
    }
    this.updateSubtitles()
  }

  componentDidUpdate() {
    this.updateSubtitles()
  }

  // destroy player on unmount
  componentWillUnmount() {
    if (this.player) {
      this.player.dispose()
    }
  }

  clickCamera = async (corner: string) => {
    const { cornerFunc, video } = this.props
    if (cornerFunc) {
      setCustomDimension(SETTINGS.ga_dimension_camera, corner)
      sendGAEvent(
        "video",
        "changeCameraView",
        video.key,
        this.player.currentTime()
      )
      await cornerFunc(corner)
      this.cropVideo()
    }
  }

  render() {
    const { video, selectedCorner, embed } = this.props
    return (
      <div className="video-odl-center">
        <div
          className={`video-odl-medium ${
            video.multiangle ? "video-odl-multiangle" : ""
          } ${embed ? "video-odl-embed" : ""}`}
          ref={node => (this.videoContainer = node)}
          style={{ position: "relative" }}
        >
          <div data-vjs-player className="vjs-big-play-centered">
            <video
              ref={node => (this.videoNode = node)}
              className={`video-js vjs-default-skin ${
                embed ? "video-odl-embed" : ""
              }`}
              crossOrigin="anonymous"
              controls
            />
          </div>
          {this.props.overlayChildren}
        </div>
        {video.multiangle && (
          <div ref={node => (this.cameras = node)} className="camera-bar">
            {Object.keys(CANVASES).map(corner => (
              <div key={corner}>
                <canvas
                  id={corner}
                  key={corner}
                  onClick={this.clickCamera.bind(this, corner)}
                  className={`camera-box ${
                    corner === selectedCorner ? "camera-box-selected" : ""
                  }`}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  setCurrentTime(time) {
    this.player.currentTime(time)
  }
}

export default connect()(VideoPlayer)
