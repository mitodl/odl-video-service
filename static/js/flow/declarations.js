// @flow
/* eslint-disable no-unused-vars */
import type {Video} from "./videoTypes"

declare var SETTINGS: {
  public_path: string,
  FEATURES: {
    [key: string]: boolean,
  },
  reactGaDebug: string,
  cloudfront_base_url: string,
  video: Video,
  videoKey: string,
  is_video_admin?: boolean,
  is_app_admin: boolean,
  is_edx_course_admin: boolean,
  user: ?string,
  email: ?string,
  dropbox_key: string,
  support_email_address: string,
  status_code?: number,
  ga_dimension_camera: string,
  sentry_dsn: string,
  release_version: string,
  environment: string
};

// mocha
declare var it: Function;
declare var beforeEach: Function;
declare var afterEach: Function;
declare var describe: Function;

// webpack
declare var __webpack_public_path__: string; // eslint-disable-line camelcase

declare var module: {
  hot: any,
}

declare var videojs: Function;

