// @flow
import R from 'ramda';

import {
  VIDEO_STATUS_CREATED,
  VIDEO_STATUS_UPLOADING,
  VIDEO_STATUS_UPLOAD_FAILED,
  VIDEO_STATUS_TRANSCODING,
  VIDEO_STATUS_TRANSCODE_FAILED_INTERNAL,
  VIDEO_STATUS_TRANSCODE_FAILED_VIDEO,
  VIDEO_STATUS_ERROR,
  ENCODING_HLS,
} from '../constants';

import type { Video } from "../flow/videoTypes";

import _videojs from 'video.js';
// For this to work properly videojs must be available as a global
global.videojs = _videojs;
require('videojs-contrib-hls');
// export here to allow mocking of videojs function
export let videojs = _videojs;

export const getHLSEncodedUrl = (video: Video): string|null => {
  const videofile = video.videofile_set.find(
    videofile => videofile.encoding === ENCODING_HLS
  );

  return videofile
    ? videofile.cloudfront_url
    : null;
};

export const videoIsProcessing = R.compose(
  R.contains(
    R.__,
    [
      VIDEO_STATUS_CREATED,
      VIDEO_STATUS_UPLOADING,
      VIDEO_STATUS_TRANSCODING,
    ]
  ),
  R.prop('status')
);

export const videoHasError = R.compose(
  R.contains(
    R.__,
    [
      VIDEO_STATUS_UPLOAD_FAILED,
      VIDEO_STATUS_TRANSCODE_FAILED_INTERNAL,
      VIDEO_STATUS_TRANSCODE_FAILED_VIDEO,
      VIDEO_STATUS_ERROR,
    ]
  ),
  R.prop('status')
);
