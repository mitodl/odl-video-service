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

const videoSubtitleId = makeCounter();

const makeObjectKey = (videoKey: string, encoding: string): string => (
  encoding === ENCODING_ORIGINAL
    ? `${videoKey}/video.mp4`
    : `transcoded/${videoKey}/video__index.m3u8`
);

const makeSubtitleObjectKey = (videoKey: string, lang: string): string => (
  `subtitles/${videoKey}/subtitle_${lang}.vtt`);

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

export const makeVideoSubtitle = (videoKey: string = casual.uuid, lang: string = 'en') => ({
  id: videoSubtitleId(),
  filename: casual.text,
  created_at: casual.moment.format(),
  s3_object_key: makeSubtitleObjectKey(videoKey, lang),
  bucket_name: casual.text,
  cloudfront_url: casual.text,
  language: lang,
  language_name: 'English'
});

export const makeVideo = (videoKey: string = casual.uuid, collectionKey: string = casual.uuid): Video => ({
  key: videoKey,
  created_at: casual.moment.format(),
  title: casual.text,
  description: casual.text,
  collection_key: collectionKey,
  collection_title: casual.text,
  collection_view_lists: [],
  multiangle: casual.coin_flip,
  videofile_set: [
    makeVideoFile(videoKey, ENCODING_HLS),
    makeVideoFile(videoKey, ENCODING_ORIGINAL),
  ],
  videothumbnail_set: [
    makeVideoThumbnail(videoKey),
  ],
  videosubtitle_set: [
    makeVideoSubtitle(videoKey),
  ],
  status: VIDEO_STATUS_COMPLETE,
  is_private: false,
  is_public: false,
  view_lists: []
});

export const makeVideos = (n: number, collectionKey: string = casual.uuid): Array<Video> => (
  // $FlowFixMe: This returns an array of Videos, Flow. I promise.
  _.times(n, () => makeVideo(casual.uuid, collectionKey))
);
