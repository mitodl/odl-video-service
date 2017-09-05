// @flow
/* global SETTINGS: false */

import type { Video } from "../flow/videoTypes";

export const makeVideoUrl = (videoKey: string) => `/videos/${encodeURI(videoKey)}`;
export const makeEmbedUrl = (videoKey: string) => `${makeVideoUrl(videoKey)}/embed/`;
export const makeCollectionUrl = (collectionKey: string) => `/collections/${encodeURI(collectionKey)}/`;
export const makeVideoThumbnailUrl = (video: Video): ?string => (
  video.videothumbnail_set && video.videothumbnail_set.length > 0
    ? `${SETTINGS.thumbnail_base_url}${video.videothumbnail_set[0].s3_object_key}`
    : null
);
