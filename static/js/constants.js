// @flow
export const ENCODING_HLS = 'HLS';
export const ENCODING_ORIGINAL = 'original';

export const MM_DD_YYYY = 'MM/DD/YYYY';

// video statuses
export const VIDEO_STATUS_CREATED = 'Created';
export const VIDEO_STATUS_UPLOADING = 'Uploading';
export const VIDEO_STATUS_UPLOAD_FAILED = 'Upload failed';
export const VIDEO_STATUS_TRANSCODING = 'Transcoding';
export const VIDEO_STATUS_TRANSCODE_FAILED_INTERNAL = 'Transcode failed internal error';
export const VIDEO_STATUS_TRANSCODE_FAILED_VIDEO = 'Transcode failed video error';
export const VIDEO_STATUS_COMPLETE = 'Complete';
export const VIDEO_STATUS_ERROR = 'Error';

export const ALL_VIDEO_STATUSES = [
  VIDEO_STATUS_CREATED,
  VIDEO_STATUS_UPLOADING,
  VIDEO_STATUS_UPLOAD_FAILED,
  VIDEO_STATUS_TRANSCODING,
  VIDEO_STATUS_TRANSCODE_FAILED_INTERNAL,
  VIDEO_STATUS_TRANSCODE_FAILED_VIDEO,
  VIDEO_STATUS_COMPLETE,
  VIDEO_STATUS_ERROR,
];

export const DIALOGS = {
  NEW_COLLECTION: 'NEW_COLLECTION',
  EDIT_VIDEO: 'EDIT_VIDEO',
  SHARE_VIDEO: 'SHARE_VIDEO'
};
