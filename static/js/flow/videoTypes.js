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

export type Video = {
  key:                string,
  created_at:         string,
  title:              string,
  description:        string,
  collection_key:     string,
  collection_title:   string,
  multiangle:         boolean,
  videofile_set:      Array<VideoFile>,
  videothumbnail_set: Array<VideoThumbnail>,
  videosubtitle_set:  Array<VideoSubtitle>,
  status:             string,
};

export type VideoUploadResult = {
  [string]: {
    s3key: string,
    title: string,
    task: string
  }
};
