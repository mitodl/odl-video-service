// @flow
import React from 'react';

import HTML5VideoPlayer from "./HTML5VideoPlayer";
import USwitchPlayer from "./USwitchPlayer";

import { makeEmbedUrl } from "../lib/urls";

import type { Video } from '../flow/videoTypes';

export default class VideoPlayer extends React.Component {
  props: {
    video: Video,
    useIframeForUSwitch: boolean,
  };

  render() {
    const { video, useIframeForUSwitch } = this.props;
    const embedUrl = makeEmbedUrl(video.key);

    if (video.multiangle) {
      if (useIframeForUSwitch) {
        return <iframe
          src={embedUrl}
          className="video-odl-medium"
          frameBorder="0"
          scrolling="no"
          allowFullScreen={true}
        />;
      } else {
        return <USwitchPlayer video={video} />;
      }
    } else {
      return <HTML5VideoPlayer video={video} />;
    }
  }
}
