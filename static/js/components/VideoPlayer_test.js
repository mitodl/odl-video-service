// @flow
import React from 'react';
import { shallow } from 'enzyme';
import { assert } from 'chai';
import VideoPlayer from './VideoPlayer';

describe("VideoPlayer", (props = {}) => {
  let renderVideoPlayer = () => {
    return shallow(
      <VideoPlayer {...props} />, {
        context: {
          router: {}
        }
      }
    );
  };

  it('video element is rendered with the correct attributes', () => {
    let wrapper = renderVideoPlayer();
    let videoProps = wrapper.find('video').props();
    assert.equal(videoProps.className, 'video-js vjs-default-skin');
    assert(videoProps.fluid === undefined);
    assert(videoProps.controls !== undefined);
  });
});
