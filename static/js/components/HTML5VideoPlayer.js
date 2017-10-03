// @flow
/* global videojs: true */
import React from 'react';

import type { Video, VideoSubtitle } from "../flow/videoTypes";
import { makeVideoSubtitleUrl } from "../lib/urls";
import { getHLSEncodedUrl, videojs } from "../lib/video";

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
   */

  props: {
    video: Video,
  };

  player: null;
  videoNode: null;


  updateSubtitles() {
    const { video } = this.props;
    if (this.player) {
      // Remove existing tracks for deleted subtitles
      const tracks = this.player.textTracks();
      let subtitleUrls = video.videosubtitle_set.map((subtitle: VideoSubtitle) => (makeVideoSubtitleUrl(subtitle)));
      let trackUrls = [];
      for (let idx = 0; idx < tracks.length; idx++) {
        if (this.player && tracks[idx] && !subtitleUrls.includes(tracks[idx].src)) {
          this.player.removeRemoteTextTrack(tracks[idx]);
        } else {
          trackUrls.push(tracks[idx].src);
        }
      }
      // Add tracks for any new subtitles associated with the video
      video.videosubtitle_set.map((subtitle: VideoSubtitle) => {
        const subUrl = makeVideoSubtitleUrl(subtitle);
        if (!trackUrls.includes(subUrl)) {
          // $FlowFixMe this.player already checked to not be null
          this.player.addRemoteTextTrack({
            kind: "captions",
            src: makeVideoSubtitleUrl(subtitle),
            srcLang: subtitle.language,
            label: subtitle.language_name
          });
        }
      });
    }
  }

  componentDidMount() {
    const { video } = this.props;
    this.player = videojs(
      this.videoNode, makeConfigForVideo(video), function onPlayerReady() {
        this.enableTouchActivity();
      }
    );
    this.updateSubtitles();
  }

  componentDidUpdate() {
    this.updateSubtitles();
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
          <video
            ref={node => this.videoNode = node}
            className="video-js vjs-default-skin"
            crossOrigin="anonymous"
            controls
          />
        </div>
      </div>
    );
  }
}
