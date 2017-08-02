// @flow
/* SETTINGS OmniPlayer: false */
import React from 'react';

export default class USwitchPlayer extends React.Component {
  /* Display the OmniPlayer for multiangle videos */

  player: null;
  videoNode: null;
  src: null;
  title: null;
  description: null;

  componentDidMount() {
    // $FlowFixMe
    this.player = OmniPlayer(); // eslint-disable-line no-undef
    const options = {
      "nbCamera": 4,
      "live": false,
      "thumbnailTop": true,
      "formats": {
        "HLS": this.props.src
      },
      "informations": {
        "poster": null,
        "title": this.props.title,
        "description": this.props.description
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
        <div ref={ node => this.videoNode = node }  id='omniPlayer'></div>
    );
  }
}
