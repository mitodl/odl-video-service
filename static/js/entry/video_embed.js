// @flow
/* global SETTINGS:false */
__webpack_public_path__ = SETTINGS.public_path;  // eslint-disable-line no-undef, camelcase
import 'react-hot-loader/patch';
import React from 'react';
import ReactDOM from 'react-dom';

import VideoEmbedPage from '../containers/VideoEmbedPage';

// Object.entries polyfill
import entries from 'object.entries';
if (!Object.entries) {
  entries.shim();
}

const rootEl = document.getElementById("container");

ReactDOM.render(
  <VideoEmbedPage
    video={SETTINGS.video}
  />,
  rootEl
);
