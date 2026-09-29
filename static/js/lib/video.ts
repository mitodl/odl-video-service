import * as R from "ramda"

import {
  VIDEO_STATUS_CREATED,
  VIDEO_STATUS_UPLOADING,
  VIDEO_STATUS_UPLOAD_FAILED,
  VIDEO_STATUS_TRANSCODING,
  VIDEO_STATUS_TRANSCODE_FAILED_INTERNAL,
  VIDEO_STATUS_TRANSCODE_FAILED_VIDEO,
  VIDEO_STATUS_ERROR,
  VIDEO_STATUS_RETRANSCODE_SCHEDULED,
  VIDEO_STATUS_RETRANSCODING,
  ENCODING_HLS
} from "../constants"
import type { Video, VideoFile } from "../types/videoTypes"

import _videojs from "video.js"
import { makeVideoFileName, makeVideoFileUrl } from "./urls"

// The Dropbox Saver widget, loaded by a <script> tag in the page template
// rather than bundled, so it has to be declared rather than imported.
declare global {
  interface Window {
    Dropbox?: {
      save: (
        url: string,
        filename: string,
        options: { error: (errorMessage: string) => void }
      ) => void
    }
  }
}

// For this to work properly videojs must be available as a global.
// globals.d.ts declares `videojs` with `const`, which TypeScript does not
// surface as a writable property of `globalThis`, hence the cast.
const globalScope = global as typeof globalThis & {
  videojs: typeof _videojs
  $: unknown
}
globalScope.videojs = _videojs
require("videojs-contrib-quality-levels")
require("videojs-hls-quality-selector")
require("videojs-youtube")
require("videojs-hotkeys")

if (SETTINGS.FEATURES.VIDEOJS_ANNOTATIONS) {
  globalScope.$ = require("jquery")
  // Loaded lazily behind a feature flag, so it cannot become a static import.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const AnnotationComments = require("@contently/videojs-annotation-comments")
  _videojs.registerPlugin("annotationComments", AnnotationComments(_videojs))
  require("@contently/videojs-annotation-comments/build/css/annotations.css")
}

// export here to allow mocking of videojs function
export const videojs = _videojs
// eslint-disable-next-line @typescript-eslint/no-var-requires
require("@silvermine/videojs-quality-selector")(videojs)

export const getHLSEncodedUrl = (video: Video): string | null => {
  const videofile = video.videofile_set.find(
    videofile => videofile.encoding === ENCODING_HLS
  )

  return videofile ? videofile.cloudfront_url : null
}

export const videoIsProcessing: (video: Video) => boolean = R.compose(
  R.includes(R.__, [
    VIDEO_STATUS_CREATED,
    VIDEO_STATUS_UPLOADING,
    VIDEO_STATUS_TRANSCODING
  ]),
  R.prop("status")
)

// All states where an async chain (upload or retranscode) is actively in-flight.
// Attempting a second replace while any of these are active would cause two
// concurrent chains to race, with the slower one overwriting the faster one.
export const videoIsInFlight: (video: Video) => boolean = R.compose(
  R.includes(R.__, [
    VIDEO_STATUS_CREATED,
    VIDEO_STATUS_UPLOADING,
    VIDEO_STATUS_TRANSCODING,
    VIDEO_STATUS_RETRANSCODE_SCHEDULED,
    VIDEO_STATUS_RETRANSCODING
  ]),
  R.prop("status")
)

export const videoHasError: (video: Video) => boolean = R.compose(
  R.includes(R.__, [
    VIDEO_STATUS_UPLOAD_FAILED,
    VIDEO_STATUS_TRANSCODE_FAILED_INTERNAL,
    VIDEO_STATUS_TRANSCODE_FAILED_VIDEO,
    VIDEO_STATUS_ERROR
  ]),
  R.prop("status")
)

export const saveToDropbox = (video: Video) => {
  const options = {
    //Simple error alert if something goes wrong with the dropbox transfer
    error: function(errorMessage: string) {
      alert(`Failed to transfer '${video.title}' to Dropbox: ${errorMessage}`)
    }
  }
  const sourceVideos = video.videofile_set.filter(
    (videofile: VideoFile) => videofile.encoding === "original"
  )
  if (sourceVideos && sourceVideos.length > 0) {
    const extension = sourceVideos[0].s3_object_key.split(".").pop()
    const videoFileUrl = makeVideoFileUrl(sourceVideos[0])
    const videoFileName = makeVideoFileName(video, extension)
    if (window.Dropbox) {
      window.Dropbox.save(videoFileUrl, videoFileName, options)
    }
  }
}
