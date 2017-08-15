// @flow
import React from 'react';
import { shallow } from 'enzyme';
import { assert } from 'chai';

import VideoPlayer from './VideoPlayer';

import { makeVideo } from '../factories/video';
import { makeEmbedUrl } from "../lib/urls";

describe('VideoPlayer', () => {
  let video;

  const renderPlayer = (props = {}) => shallow(
    <VideoPlayer video={video} useIframeForUSwitch={false} {...props} />
  );

  beforeEach(() => {
    video = makeVideo();
  });

  it('renders a component for HTML5 video', () => {
    video.multiangle = false;
    let wrapper = renderPlayer();
    assert.deepEqual(wrapper.find("HTML5VideoPlayer").props(), {
      video,
    });
  });

  it('renders a component for USwitch video without an iframe', () => {
    video.multiangle = true;
    let wrapper = renderPlayer();
    assert.deepEqual(wrapper.find("USwitchPlayer").props(), {
      video,
    });
  });

  it('renders an iframe for playing USwitch video', () => {
    video.multiangle = true;
    let wrapper = renderPlayer({ useIframeForUSwitch: true });
    assert.deepEqual(wrapper.find("iframe").props(), {
      allowFullScreen: true,
      className: "video-odl-medium",
      frameBorder: "0",
      scrolling: "no",
      src: makeEmbedUrl(video.key),
    });
  });
});
