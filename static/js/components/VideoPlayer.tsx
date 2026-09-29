import React from "react"
import * as R from "ramda"
import _ from "lodash"
import type { Dispatch } from "redux"
import { videojs } from "../lib/video"
import {
  VideoPlayerController,
  isFullscreen
} from "../lib/video_player_controller"
import type { VideoJsPlayer } from "../lib/video_player_controller"
import type { Video, VideoSource } from "../types/videoTypes"
import type { ActionCreator } from "../types/reduxTypes"
import { FULLSCREEN_API } from "../util/fullscreen_api"
import { CANVASES } from "../constants"
import { sendGAEvent, setCustomDimension } from "../util/google_analytics"
import { actions } from "../actions"
import { connect } from "react-redux"

/*
 * One rendition in the HLS master playlist, as videojs-contrib-hls exposes it
 * on `tech_.hls`. Only the two fields selectPlaylist reads are described: the
 * plugin is loaded for its side effects in lib/video and ships no types.
 */
type HlsPlaylist = {
  disabled?: boolean
  attributes: {
    BANDWIDTH: number
  }
}

/*
 * The player members this component drives, on top of the geometry/subtitle
 * slice VideoPlayerController already declares. video.js ships types for its
 * Player class, but they describe neither the `el_`/`tech_` privates this
 * component reaches for nor the plugins registered at runtime (hotkeys,
 * hlsQualitySelector, annotationComments), and the tests hand the component a
 * plain stub rather than a real player -- so the structural type is extended
 * here rather than swapped for video.js's own.
 */
type ComponentPlayer = VideoJsPlayer & {
  el_: {
    style: {
      [key: string]: string
    }
    dispatchEvent: (event: Event) => void
  }
  tech_: {
    currentTime: () => number
    hls?: {
      systemBandwidth: number
      selectPlaylist: () => HlsPlaylist
      playlists: {
        master: {
          playlists: Array<HlsPlaylist>
        }
      }
    }
  }
  src: (sources: Array<VideoSource>) => void
  on: (event: string, handler: () => void) => void
  // The controller only ever reads the time; setCurrentTime also sets it.
  currentTime: (time?: number) => number
  duration: () => number
  dispose: () => void
  annotationComments: (options: {
    annotationsObjects: Array<unknown>
    meta: {
      user_name: string | null
      user_id: string | null
    }
    startInAnnotationMode: boolean
  }) => void
}

/*
 * `this` inside the onPlayerReady callback is the player video.js just built.
 * video.js types it as Player, which does not carry the hotkeys plugin
 * lib/video registers, so that one member is added back here.
 */
type ReadyPlayer = {
  enableTouchActivity: () => void
  hotkeys: (options: {
    volumeStep: number
    seekStep: number
    enableModifiersForNumbers: boolean
  }) => void
  on: (event: string, handler: () => void) => void
  currentTime: (time: number) => void
  tech_: ComponentPlayer["tech_"]
}

/*
 * `actions` is declared `Record<string, unknown>` in actions/index.ts, so each
 * slice comes back as `unknown`. The cast is erased at runtime -- the calls
 * stay property accesses on `actions.videoUi`, which is what the tests stub --
 * and only tells tsc the shape actions/videoUi.ts already exports.
 */
type VideoUiActions = {
  setVideoTime: ActionCreator
  setVideoDuration: ActionCreator
}

type VideoJsConfig = {
  autoplay: boolean
  poster: string | undefined
  controls: boolean
  fluid: boolean
  playsinline: boolean
  techOrder: Array<string>
  html5: {
    nativeTextTracks: boolean
    hls: {
      overrideNative: boolean
    }
  }
  playbackRates: Array<number>
  sources: Array<VideoSource> | Array<{ type: string; src: string }>
  src: Array<VideoSource>
  youtube: {
    ytControls: number
    start: number
  }
  plugins: {
    hlsQualitySelector: Record<string, unknown>
  }
  controlBar: {
    children: Array<string>
  }
}

type Props = {
  dispatch: Dispatch
  video: Video
  selectedCorner: string
  cornerFunc: (corner: string) => void
  embed: boolean | null
  videoPlayerRef?: (player: VideoPlayer) => void
  overlayChildren?: React.ReactNode
}

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
  embedded: boolean | null,
  startTime: number
): VideoJsConfig => ({
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

export class VideoPlayer extends React.Component<Props> {
  player: ComponentPlayer
  controller: VideoPlayerController = new VideoPlayerController()
  lastMinuteTracked: number | null

  updateSubtitles = () => this.controller.updateSubtitles(this.props.video)

  cropVideo = () => this.controller.cropVideo(this.props.selectedCorner)

  resizeYouTube = () => this.controller.resizeYouTube(this.props.embed)

  toggleFullscreen = () => {
    const fullscreen = isFullscreen()
    if (fullscreen) {
      // FULLSCREEN_API resolves to whichever vendor-prefixed key this browser
      // supports, so the property is not in the DOM lib's Document definition.
      document[FULLSCREEN_API.exitFullscreen]()
    } else {
      const { videoContainer } = this.controller
      if (!videoContainer) {
        // Make the typechecker happy -- toggleFullscreen is only reachable
        // from the control bar, which video.js builds after render() sets the
        // ref.
        throw new Error("Missing videoContainer")
      }
      // videoContainer is the .video-odl-medium div, which render() always
      // emits inside .video-odl-center, so parentElement is never null.
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
      // parseInt coerced this number to a string on its own; String() makes
      // the identical conversion explicit for the typechecker.
      const nearestMinute = parseInt(
        String((currentTime - (currentTime % 60)) / 60)
      )
      if (this.lastMinuteTracked !== nearestMinute) {
        sendGAEvent(
          "video",
          "T".concat(nearestMinute.toString().padStart(4, "0")),
          label,
          1
        )
        this.lastMinuteTracked = nearestMinute
      }
      dispatch(
        (actions.videoUi as VideoUiActions).setVideoTime(
          Math.floor(currentTime)
        )
      )
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
    const sortByBandwidth = R.sortBy<HlsPlaylist>(
      R.path(["attributes", "BANDWIDTH"])
    )
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
      // handleClick lives on ClickableComponent, which video.js's types do not
      // expose through the base Component that getComponent is declared to
      // return.
      const fullscreenToggle = videojs.getComponent("FullscreenToggle")
        .prototype as unknown as { handleClick: () => void }
      fullscreenToggle.handleClick = toggleFullscreen
    }
    const useYouTube = video.is_public && video.youtube_id !== null
    this.lastMinuteTracked = null
    const selectPlaylist = this.selectPlaylist.bind(this)
    // The onPlayerReady callbacks below are plain functions, not arrows:
    // video.js calls them with the player as `this`, so the component has to
    // reach itself through a captured alias rather than through `this`.
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const self = this
    const params = new URLSearchParams(window.location.search)
    const startTime = parseInt(params.get("start")) || 0
    this.player = videojs(
      this.controller.videoNode,
      makeConfigForVideo(video, useYouTube, embed, startTime),
      function onPlayerReady(this: ReadyPlayer) {
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
        this.on("loadedmetadata", function(this: ReadyPlayer) {
          self.props.dispatch(
            (actions.videoUi as VideoUiActions).setVideoDuration(
              self.player.duration()
            )
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
      } as () => void
    ) as unknown as ComponentPlayer
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
          ref={node => {
            this.controller.videoContainer = node
          }}
          style={{ position: "relative" }}
        >
          <div data-vjs-player className="vjs-big-play-centered">
            <video
              ref={node => {
                this.controller.videoNode = node
              }}
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
            ref={node => {
              this.controller.cameras = node
            }}
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

  setCurrentTime(time: number) {
    this.player.currentTime(time)
  }
}

export default connect()(VideoPlayer)
