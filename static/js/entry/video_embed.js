// @flow
/* global SETTINGS:false */

__webpack_public_path__ = SETTINGS.public_path;  // eslint-disable-line no-undef, camelcase
import 'react-hot-loader/patch';
import React from 'react';
import ReactDOM from 'react-dom';
import { Provider } from 'react-redux';

import configureStore from "../store/configureStore";
import VideoEmbedPage from '../containers/VideoEmbedPage';

// Object.entries polyfill
import entries from 'object.entries';
if (!Object.entries) {
  entries.shim();
}

const store = configureStore();

const rootEl = document.getElementById("container");

ReactDOM.render(
  <Provider store={store}>
    <VideoEmbedPage
      video={SETTINGS.video}
    />
  </Provider>,
  rootEl
);
