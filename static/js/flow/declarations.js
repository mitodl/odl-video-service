// @flow
/* eslint-disable no-unused-vars */
declare var SETTINGS: {
  public_path: string,
  FEATURES: {
    [key: string]: boolean,
  },
  reactGaDebug: string,
  cloudfront_base_url: string,
  video: Video,
  videoKey: string,
  editable: boolean,
  user: ?string,
  email: ?string,
  dropbox_key: string,
  support_email_address: string,
  status_code?: number
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

