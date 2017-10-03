// @flow
import React from 'react';

import VideoPlayer from '../components/VideoPlayer';

import type { Video } from "../flow/videoTypes";

export default class VideoEmbedPage extends React.Component {
  props: {
    video: Video,
  };

  render() {
    const { video } = this.props;

    return <div className="embedded-video">
      <VideoPlayer
        video={video}
        useIframeForUSwitch={false}
      />
    </div>;
  }
}
