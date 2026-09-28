import type { DescriptionFormat } from "./descriptionTypes"

export type VideoSubtitle = {
  id: number
  created_at: string
  s3_object_key: string
  bucket_name: string
  cloudfront_url: string
  language: string
  language_name: string
  filename: string
}

export type VideoFile = {
  id: number
  created_at: string
  s3_object_key: string
  encoding: string
  bucket_name: string
  cloudfront_url: string
}

export type VideoThumbnail = {
  id: number
  created_at: string
  s3_object_key: string
  bucket_name: string
  cloudfront_url: string
}

export type VideoSource = {
  src: string
  label: string
  type: string
}

export type Video = {
  key: string
  created_at: string
  title: string
  description: string
  description_format: DescriptionFormat
  collection_key: string
  collection_title: string
  multiangle: boolean
  videofile_set: Array<VideoFile>
  videothumbnail_set: Array<VideoThumbnail>
  videosubtitle_set: Array<VideoSubtitle>
  status: string
  view_lists: Array<string>
  collection_view_lists: Array<string>
  is_public: boolean
  is_private: boolean
  is_logged_in_only: boolean
  sources: Array<VideoSource>
  youtube_id: string | null
  cloudfront_url: string
}

export type VideoUpdatePayload = {
  title: string
  description: string
  description_format?: DescriptionFormat
  cta_link?: string | null
  view_lists?: Array<string>
  is_logged_in_only?: boolean
  is_private?: boolean
  is_public?: boolean
}

export type VideoFormState = {
  key: string | null
  title: string | null
  description: string | null
  description_format: DescriptionFormat | null
  // Optional, not `string | null`: INITIAL_EDIT_VIDEO_FORM_STATE in
  // reducers/videoUi omits this key entirely, so it reads `undefined` until
  // SET_EDIT_VIDEO_CTA_LINK fires. The Flow type claimed it was always
  // present and nothing checked. Recording reality here rather than adding
  // the key -- changing runtime state shape is not a type migration's job.
  cta_link?: string | null
  overrideChoice: string
  viewChoice: string
  viewLists: string | null
}

export type VideoShareState = {
  shareTime: boolean
  videoTime: number
}

export type VideoSubtitleState = {
  key: string | null
  language: string
  subtitle: File | null
}

export type VideoValidation = {
  title?: string
  view_lists?: string
}

export type VideoUiState = {
  editVideoForm: VideoFormState
  videoSubtitleForm: VideoSubtitleState
  shareVideoForm: VideoShareState
  corner: string
  errors?: VideoValidation
  videoTime: number
  duration: number
  analyticsOverlayIsVisible: boolean
  currentVideoKey: string | null
  currentSubtitlesKey: string | number | null
}
