// @flow
/* global OmniPlayer: false */
import React from 'react';

import { getHLSEncodedUrl } from '../lib/video';
import type { Video } from "../flow/videoTypes";

export default class USwitchPlayer extends React.Component {
  /* Display the OmniPlayer for multiangle videos */

  props: {
    video: Video,
  };

  player: null;

  componentDidMount() {
    const { video } = this.props;

    this.player = OmniPlayer();
    const options = {
      "nbCamera": 4,
      "live": false,
      "thumbnailTop": false,
      "formats": {
        "HLS": getHLSEncodedUrl(video),
      },
      "informations": {
        "poster": null,
        "title": video.title,
        "description": video.description
      },
      "configuration": {
        "defaultFormat": 1,
        "defaultCamera": 1,
        "defaultPinned": true,
        "defaultPinnedPosition": "right",
        "defaultLang": "English"
      },
      "userInterface": {
        "community": {
        },
        "camera": [{
          "text": "Camera 1",
        }, {
          "text": "Camera 2",
        }, {
          "text": "Camera 3",
        }, {
          "text": "Camera 4",
        }
        ]
      }
    };
    // $FlowFixMe: Flow thinks this.player might be null
    this.player.load(options);
  }

  // destroy player on unmount
  componentWillUnmount() {
    if (this.player) {
      this.player.dispose();
    }
  }

  render() {
    return (
      <div allowFullScreen id='omniPlayer'>
        <video id='video' />
      </div>
    );
  }
}
