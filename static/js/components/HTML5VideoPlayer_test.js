// @flow
import React from 'react';
import { mount } from 'enzyme';
import { assert } from 'chai';
import sinon from 'sinon';

import { makeVideo } from '../factories/video';
import HTML5VideoPlayer from './HTML5VideoPlayer';
import * as libVideo from "../lib/video";

describe("HTML5VideoPlayer", (props = {}) => {
  let sandbox, videojsStub, video;

  beforeEach(() => {
    video = makeVideo();
    sandbox = sinon.sandbox.create();
    videojsStub = sandbox.stub(libVideo, 'videojs');
  });

  afterEach(() => {
    sandbox.restore();
  });

  let renderVideoPlayer = () => {
    video.multiangle = false;
    return mount(
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

  it('uses videojs on mount with the right arguments', () => {
    renderVideoPlayer();
    sinon.assert.called(videojsStub);
    let args = videojsStub.firstCall.args;
    assert.equal(args[0].tagName, "VIDEO");
    assert.deepEqual(args[1], {
      autoplay: true,
      controls: true,
      fluid: false,
      sources: [
        {
          type: 'application/x-mpegURL',
          src: libVideo.getHLSEncodedUrl(video),
        }
      ]
    });
    let enableTouchActivityStub = sandbox.stub();
    args[2].call({
      enableTouchActivity: enableTouchActivityStub
    });
    sinon.assert.calledWith(enableTouchActivityStub);
  });
});
