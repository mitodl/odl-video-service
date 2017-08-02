/* global SETTINGS: false */
require('react-hot-loader/patch');
const $script = require('scriptjs');
import React from 'react';
import ReactDOM from 'react-dom';

import USwitchPlayer from '../components/USwitchPlayer';
const videoSource = SETTINGS.videofile; // eslint-disable-line no-undef
const uswitchPlayerURL = SETTINGS.uswitchPlayerURL;

$script(`${uswitchPlayerURL}/lib/omni-external-libs.js`, function () {
  $script(`${uswitchPlayerURL}/lib/omni-min.js`, function () {
    $script(`${uswitchPlayerURL}/lib/hls.min.js`, function () {
      const videoDiv = document.querySelector('#odl-video-player');
      if (videoDiv) {
        ReactDOM.render(
          <USwitchPlayer id='omniPlayer' src={videoSource.src}
            description={videoSource.description}
            title={videoSource.title}/>, videoDiv);
      }
    });
  });
});



