// @flow
/* global SETTINGS: false */
import R from "ramda"

import {
  VIDEO_STATUS_CREATED,
  VIDEO_STATUS_UPLOADING,
  VIDEO_STATUS_UPLOAD_FAILED,
  VIDEO_STATUS_TRANSCODING,
  VIDEO_STATUS_TRANSCODE_FAILED_INTERNAL,
  VIDEO_STATUS_TRANSCODE_FAILED_VIDEO,
  VIDEO_STATUS_ERROR,
  ENCODING_HLS
} from "../constants"
import type { Video, VideoFile } from "../flow/videoTypes"

import _videojs from "video.js"
import { makeVideoFileName, makeVideoFileUrl } from "./urls"

// For this to work properly videojs must be available as a global
global.videojs = _videojs
require("videojs-contrib-quality-levels")
require("videojs-hls-quality-selector")
require("videojs-youtube")
require("videojs-hotkeys")

// export here to allow mocking of videojs function
export const videojs = _videojs
require("@silvermine/videojs-quality-selector")(videojs)

export const getHLSEncodedUrl = (video: Video): string | null => {
  const videofile = video.videofile_set.find(
    videofile => videofile.encoding === ENCODING_HLS
  )

  return videofile ? videofile.cloudfront_url : null
}

export const videoIsProcessing = R.compose(
  R.contains(R.__, [
    VIDEO_STATUS_CREATED,
    VIDEO_STATUS_UPLOADING,
    VIDEO_STATUS_TRANSCODING
  ]),
  R.prop("status")
)

export const videoHasError = R.compose(
  R.contains(R.__, [
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
