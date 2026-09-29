import sanitize from "sanitize-filename"

import type { Video, VideoFile, VideoSubtitle } from "../types/videoTypes"

export const makeVideoUrl = (videoKey: string) =>
  `/videos/${encodeURI(videoKey)}/`
export const makeEmbedUrl = (videoKey: string) =>
  `${makeVideoUrl(videoKey)}embed/`
export const makeCollectionUrl = (collectionKey: string) =>
  `/collections/${encodeURI(collectionKey)}/`

// The only one here that can actually be null. Flow annotated all six as
// `?string`, but the other five return a template literal unconditionally.
export const makeVideoThumbnailUrl = (video: Video): string | null =>
  video.videothumbnail_set && video.videothumbnail_set.length > 0 ?
    `${SETTINGS.cloudfront_base_url}${video.videothumbnail_set[0].s3_object_key}` :
    null

export const makeVideoFileUrl = (videoFile: VideoFile): string =>
  `${SETTINGS.cloudfront_base_url}${encodeURI(videoFile.s3_object_key)}`

export const makeVideoFileName = (video: Video, extension: string): string =>
  sanitize(
    video.title + (video.title.endsWith(extension) ? "" : `.${extension}`)
  )

export const makeVideoSubtitleUrl = (videoSubtitle: VideoSubtitle): string =>
  `${SETTINGS.cloudfront_base_url}${videoSubtitle.s3_object_key}`
