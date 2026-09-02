// @flow
/* global videojs: true */
/* global SETTINGS: false */
import React from "react"
import * as R from "ramda"
import _ from "lodash"
import type { Dispatch } from "redux"
import { videojs } from "../lib/video"
import {
  VideoPlayerController,
  isFullscreen
} from "../lib/video_player_controller"
import type { Video } from "../flow/videoTypes"
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
  autoplay: false,
  poster:
    !useYouTube && video.videothumbnail_set.length > 0 ?
      video.videothumbnail_set[0].cloudfront_url :
      undefined,
  controls:    true,
  fluid:       embedded || false,
  playsinline: true,
  techOrder:   useYouTube ? ["youtube", "html5"] : ["html5"],
  html5:       {
    nativeTextTracks: false,
    hls:              {
      overrideNative: true
    }
  },
  playbackRates: [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0],
  sources:       useYouTube ?
    [
      {
        type: "video/youtube",
        src:  `https://www.youtube.com/watch?v=${video.youtube_id || ""}`
      }
    ] :
    video.sources,
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
  controller: VideoPlayerController = new VideoPlayerController()
  lastMinuteTracked: ?number

  updateSubtitles = () => this.controller.updateSubtitles(this.props.video)

  cropVideo = () => this.controller.cropVideo(this.props.selectedCorner)

  resizeYouTube = () => this.controller.resizeYouTube(this.props.embed)

  toggleFullscreen = () => {
    const fullscreen = isFullscreen()
    if (fullscreen) {
      // FULLSCREEN_API resolves to whichever vendor-prefixed key this browser
      // supports, so the property is not in Flow's HTMLDocument definition.
      // $FlowFixMe
      document[FULLSCREEN_API.exitFullscreen]()
    } else {
      const { videoContainer } = this.controller
      if (!videoContainer) {
        // Make flow happy -- toggleFullscreen is only reachable from the
        // control bar, which video.js builds after render() sets the ref.
        throw new Error("Missing videoContainer")
      }
      // videoContainer is the .video-odl-medium div, which render() always
      // emits inside .video-odl-center, so parentElement is never null.
      // $FlowFixMe Flow cannot prove that from the ref's type
      videoContainer.parentElement[FULLSCREEN_API.requestFullscreen]()
    }
    this.player.el_.dispatchEvent(
      new Event(`fullscreen ${fullscreen ? "off" : "on"}`)
    )
  }

  switchVideoSource = () => {
    const { video } = this.props
    if (video.sources.length > 0) {
      this.player.src(video.sources)
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
      const nearestMinute = parseInt((currentTime - (currentTime % 60)) / 60)
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
      this.controller.videoNode,
      makeConfigForVideo(video, useYouTube, embed, startTime),
      function onPlayerReady() {
        this.enableTouchActivity()
        this.hotkeys({
          volumeStep:                0.1,
          seekStep:                  5,
          enableModifiersForNumbers: false
        })
        if (video.multiangle) {
          setCustomDimension(SETTINGS.ga_dimension_camera, selectedCorner)
          this.on("loadeddata", cropVideo)
          this.on(FULLSCREEN_API.fullscreenchange, cropVideo)
          window.addEventListener("resize", cropVideo)
        } else if (useYouTube) {
          this.on("loadedmetadata", resizeYouTube)
          window.addEventListener("resize", resizeYouTube)
        }
        this.on("loadedmetadata", function() {
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
        self.updateSubtitles()
      }
    )
    this.controller.player = this.player
    if (SETTINGS.FEATURES.VIDEOJS_ANNOTATIONS) {
      this.player.annotationComments({
        annotationsObjects: [],
        meta:               {
          user_name: SETTINGS.user || null,
          user_id:   SETTINGS.user || null
        },
        startInAnnotationMode: true
      })
    }
    if (useYouTube) {
      this.checkYouTube()
    }
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
          ref={node => (this.controller.videoContainer = node)}
          style={{ position: "relative" }}
        >
          <div data-vjs-player className="vjs-big-play-centered">
            <video
              ref={node => (this.controller.videoNode = node)}
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
          <div
            ref={node => (this.controller.cameras = node)}
            className="camera-bar"
          >
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
