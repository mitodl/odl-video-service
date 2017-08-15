// @flow
import React from 'react';
import { shallow } from 'enzyme';
import { assert } from 'chai';

import { makeVideo } from '../factories/video';
import HTML5VideoPlayer from './HTML5VideoPlayer';

describe("HTML5VideoPlayer", (props = {}) => {
  let renderVideoPlayer = () => {
    const video = makeVideo();
    video.multiangle = false;
    return shallow(
      <HTML5VideoPlayer
        video={video}
        {...props}
      />
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
