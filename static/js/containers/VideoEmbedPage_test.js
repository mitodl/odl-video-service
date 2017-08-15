// @flow
import React from 'react';
import { shallow } from 'enzyme';
import { assert } from 'chai';

import VideoEmbedPage from "./VideoEmbedPage";

import { makeVideo } from "../factories/video";

describe('VideoEmbedPage', () => {
  it('renders a VideoPlayer component', () => {
    const video = makeVideo();
    const wrapper = shallow(<VideoEmbedPage video={video} />);
    assert.deepEqual(wrapper.find("VideoPlayer").props(), {
      video: video,
      useIframeForUSwitch: false,
    });
  });
});
