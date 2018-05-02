// @flow

export type VideoSubtitle = {
  id:             number,
  created_at:     string,
  s3_object_key:  string,
  bucket_name:    string,
  cloudfront_url: string,
  language:       string,
  language_name:  string,
  filename:       string
}

export type VideoFile = {
  id:             number,
  created_at:     string,
  s3_object_key:  string,
  encoding:       string,
  bucket_name:    string,
  cloudfront_url: string,
};

export type VideoThumbnail = {
  id:            number,
  created_at:    string,
  s3_object_key: string,
  bucket_name:   string,
};

export type VideoSource = {
  src:           string,
  label:         string,
  type:          string,
};

export type Video = {
  key:                    string,
  created_at:             string,
  title:                  string,
  description:            string,
  collection_key:         string,
  collection_title:       string,
  multiangle:             boolean,
  videofile_set:          Array<VideoFile>,
  videothumbnail_set:     Array<VideoThumbnail>,
  videosubtitle_set:      Array<VideoSubtitle>,
  status:                 string,
  view_lists:             Array<string>,
  collection_view_lists:   Array<string>,
  is_public:              boolean,
  is_private:             boolean,
  sources:                Array<VideoSource>,
  youtube_id:            ?string
};

export type VideoFormState = {
  key: ?string,
  title: ?string,
  description: ?string,
  overrideChoice: string,
  viewChoice: string,
  viewLists: ?string
};

export type VideoShareState = {
  shareTime: boolean,
  videoTime: number
};

export type VideoSubtitleState = {
  key: ?string,
  language: string,
  subtitle: ?File
};

export type VideoValidation = {
  title?:  string,
  view_lists?: string,
}

export type VideoUiState = {
  editVideoForm: VideoFormState,
  videoSubtitleForm: VideoSubtitleState,
  shareVideoForm: VideoShareState,
  corner: string,
  errors?: VideoValidation,
  videoTime: number,
  duration: number,
  analyticsOverlayIsVisible: boolean,
  currentVideoKey: ?string,
  currentSubtitlesKey: ?(string|number)
};
