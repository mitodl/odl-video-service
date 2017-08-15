import React from 'react';
import { shallow } from 'enzyme';
import { assert } from 'chai';

import USwitchPlayer from './USwitchPlayer';
import { makeVideo } from "../factories/video";

describe("USwitchPlayer", () => {
  let renderVideoPlayer = () => {
    const video = makeVideo();
    video.multiangle = true;
    return shallow(
      <USwitchPlayer video={video} />
    );
  };

  it('div element with id of omniPlayer is rendered', () => {
    let wrapper = renderVideoPlayer();
    assert.equal(wrapper.html(),'<div allowfullscreen="" id="omniPlayer"><video id="video"></video></div>');
  });
});
