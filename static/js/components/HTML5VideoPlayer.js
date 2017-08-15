// @flow
/* global videojs: true */
import React from 'react';

import videojs from 'video.js';
// For this to work properly videojs must be available as a global
global.videojs = videojs;
require('videojs-contrib-hls');

import { getHLSEncodedUrl } from "../lib/video";

import type { Video } from "../flow/videoTypes";

const makeConfigForVideo = (video: Video): Object => ({
  autoplay: true,
  controls: true,
  fluid: false,
  sources: [{
    src: getHLSEncodedUrl(video),
    type: 'application/x-mpegURL',
  }]
});

export default class HTML5VideoPlayer extends React.Component {
  /*
    Basic component based on https://github.com/videojs/video.js/blob/master/docs/guides/react.md
    TODO: Add more configuration options, including optional rendering of <TextTrack> elements for subtitles.
   */

  props: {
    video: Video,
  };

  player: null;
  videoNode: null;

  componentDidMount() {
    const { video } = this.props;

    this.player = videojs(
      this.videoNode, makeConfigForVideo(video), function onPlayerReady() {
        this.enableTouchActivity();
      }
    );
  }

  // destroy player on unmount
  componentWillUnmount() {
    if (this.player) {
      this.player.dispose();
    }
  }

  render() {
    return (
      <div className="video-odl-medium">
        <div data-vjs-player>
          <video ref={ node => this.videoNode = node } className="video-js vjs-default-skin" controls />
        </div>
      </div>
    );
  }
}
