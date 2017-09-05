// @flow
import _ from "lodash";
import casual from "casual-browserify";

import {
  ENCODING_HLS,
  ENCODING_ORIGINAL,
  VIDEO_STATUS_COMPLETE,
} from "../constants";
import { makeCounter } from "../util/test_utils";

import type { Video } from "../flow/videoTypes";

const videoFileId = makeCounter();

const videoThumbnailId = makeCounter();

const makeObjectKey = (videoKey: string, encoding: string): string => (
  encoding === ENCODING_ORIGINAL
    ? `${videoKey}/video.mp4`
    : `transcoded/${videoKey}/video__index.m3u8`
);

export const makeVideoFile = (videoKey: string = casual.uuid, encoding: string = ENCODING_ORIGINAL) => ({
  id: videoFileId(),
  created_at: casual.moment.format(),
  s3_object_key: makeObjectKey(videoKey, encoding),
  encoding: encoding,
  bucket_name: casual.text,
  cloudfront_url: `https://fake.cloudfront.fake/${makeObjectKey(videoKey, encoding)}`,
});

export const makeVideoThumbnail = (videoKey: string = casual.uuid, encoding: string = ENCODING_ORIGINAL) => ({
  id: videoThumbnailId(),
  created_at: casual.moment.format(),
  s3_object_key: makeObjectKey(videoKey, encoding),
  bucket_name: casual.text,
});

export const makeVideo = (videoKey: string = casual.uuid, collectionKey: string = casual.uuid): Video => ({
  key: videoKey,
  created_at: casual.moment.format(),
  title: casual.text,
  description: casual.text,
  collection_key: collectionKey,
  collection_title: casual.text,
  multiangle: casual.coin_flip,
  videofile_set: [
    makeVideoFile(videoKey, ENCODING_HLS),
    makeVideoFile(videoKey, ENCODING_ORIGINAL),
  ],
  videothumbnail_set: [
    makeVideoThumbnail(videoKey),
  ],
  status: VIDEO_STATUS_COMPLETE,
});

export const makeVideos = (n: number, collectionKey: string = casual.uuid): Array<Video> => (
  // $FlowFixMe: This returns an array of Videos, Flow. I promise.
  _.times(n, () => makeVideo(casual.uuid, collectionKey))
);
