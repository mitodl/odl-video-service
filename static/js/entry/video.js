/* global SETTINGS: false */
require('react-hot-loader/patch');
require('videojs5-hlsjs-source-handler');
import 'expose-loader?videojs!video.js'; // Needs to be available as a global

import React from 'react';
import ReactDOM from 'react-dom';

import VideoPlayer from '../components/VideoPlayer';
const videoSource = SETTINGS.videofile; // eslint-disable-line no-undef

const videoJsOptions = {
  autoplay: true,
  controls: true,
  fluid: false,
  sources: [{
    src: videoSource,
    type: 'application/x-mpegURL'
  }]
};

const videoDiv = document.querySelector('#odl-video-player');
if (videoDiv) {
  ReactDOM.render(<VideoPlayer { ...videoJsOptions }/>, videoDiv);
}


