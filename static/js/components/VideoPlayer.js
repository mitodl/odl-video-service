// @flow
/* SETTINGS videojs: false */
import React from 'react';

/**
 * Before using, import the following (as in ../entry/videojs):
 *     require('videojs5-hlsjs-source-handler');
 *     import 'expose-loader?videojs!video.js';
 * These are not imported here due to babel issues
 * with expose-loader & a hlsjs dependency that cause
 * tests to fail.
 */

export default class VideoPlayer extends React.Component {
  /*
    Basic component based on https://github.com/videojs/video.js/blob/master/docs/guides/react.md
    TODO: Add more configuration options, including optional rendering of <TextTrack> elements for subtitles.
   */

  player: null;
  videoNode: null;

  componentDidMount() {
    // $FlowFixMe
    this.player = videojs(this.videoNode, this.props, function onPlayerReady() { // eslint-disable-line no-undef
      this.enableTouchActivity();
    });
  }

  // destroy player on unmount
  componentWillUnmount() {
    if (this.player) {
      this.player.dispose();
    }
  }

  render() {
    return (
      <div data-vjs-player>
        <video ref={ node => this.videoNode = node } className="video-js vjs-default-skin" controls></video>
      </div>
    );
  }
}
