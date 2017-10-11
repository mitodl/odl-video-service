// @flow
import React from 'react';
import { assert } from 'chai';
import sinon from 'sinon';
import { mount, shallow } from 'enzyme';

import VideoPlayer from './VideoPlayer';
import {makeVideo, makeVideoSubtitle} from '../factories/video';
import * as libVideo from "../lib/video";
import { CANVASES } from "../constants";
import {makeVideoSubtitleUrl} from "../lib/urls";

describe('VideoPlayer', (props = {}) => {
  let video, videojsStub, sandbox, cornerFunction, playerStub, containerStub, nodeStub;


  const renderPlayer = (props = {}) => shallow(
    <VideoPlayer
      video={video}
      cornerFunc={cornerFunction}
      selectedCorner={Object.keys(CANVASES)[0]}
      {...props}
    />
  );

  const mountPlayer = () => {
    video.multiangle = false;
    return mount(
      <VideoPlayer
        video={video}
        cornerFunc={cornerFunction}
        selectedCorner={Object.keys(CANVASES)[0]}
        {...props}
      />
    );
  };

  beforeEach(() => {
    video = makeVideo();
    sandbox = sinon.sandbox.create();
    videojsStub = sandbox.stub(libVideo, 'videojs');
    cornerFunction = sandbox.stub();
    playerStub = {
      el_: {
        style: {}
      },
      tracks: [],
      videoWidth: function() {return 640;},
      videoHeight: function() {return 360;},
      currentWidth: function() {return 1280;},
      currentHeight: function() {return 720;},
      textTracks: function() {return this.tracks;},
      removeRemoteTextTrack: function(track) {this.tracks.splice(this.tracks.indexOf(track),1);},
      addRemoteTextTrack: function(track) {this.tracks.push({src: track.src});}
    };
    containerStub = {style: {}, parentElement: {style: {}}};
    nodeStub = {style: {}};
  });

  afterEach(() => {
    sandbox.restore();
  });

  it('uses videojs on mount with the right arguments', () => {
    mountPlayer();
    sinon.assert.called(videojsStub);
    let args = videojsStub.firstCall.args;
    assert.equal(args[0].tagName, "VIDEO");
    assert.deepEqual(args[1], {
      autoplay: false,
      controls: true,
      fluid: false,
      playsinline: true,
      html5: {
        nativeTextTracks: false
      },
      playbackRates: [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0],
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

  it('video element is rendered with the correct attributes', () => {
    let wrapper = renderPlayer();
    let videoProps = wrapper.find('video').props();
    assert.equal(videoProps.className, 'video-js vjs-default-skin');
    assert(videoProps.fluid === undefined);
    assert(videoProps.controls !== undefined);
  });

  it('video element is rendered with 4 canvas elements when multiangle', () => {
    video.multiangle = true;
    let wrapper = renderPlayer();
    let canvases = wrapper.find('.camera-box');
    assert.equal(canvases.length, 4);
  });

  it('video element is rendered with 1 selected canvas elements when multiangle', () => {
    video.multiangle = true;
    let wrapper = renderPlayer();
    let canvas = wrapper.find('.camera-box-selected').at(0);
    assert.equal(canvas.props().id, 'upperLeft');
  });

  it('selected video screen changes on click', () => {
    video.multiangle = true;
    let wrapper = renderPlayer();
    let canvases = wrapper.find('.camera-box');
    canvases.at(3).prop('onClick')();
    sinon.assert.calledWith(cornerFunction, 'lowerRight');
  });

  it('cropVideo modifies style and configureCameras function called', () => {
    video.multiangle = true;
    sandbox.stub(window, 'getComputedStyle').returns({maxHeight: 600});
    let wrapper = renderPlayer();
    wrapper.instance().player = playerStub;
    wrapper.instance().videoNode = nodeStub;
    wrapper.instance().videoContainer = containerStub;
    wrapper.instance().cropVideo();
    assert.deepEqual(wrapper.instance().videoNode.style,
      {
        "left": "640px",
        "top": "360px",
        "transform": "scale(2)"
      }
    );
  });

  it('drawCanvas calls inner drawCanvasImage', () => {
    video.multiangle = true;
    sandbox.stub(window, 'getComputedStyle').returns({maxHeight: 600});
    let wrapper = renderPlayer();
    wrapper.instance().player = playerStub;
    wrapper.instance().videoNode = nodeStub;
    let canvas = wrapper.find('.camera-box').at(0);
    assert.throws(() => wrapper.instance().drawCanvas(canvas, true, false), TypeError, 'getContext');
  });

  it('subtitles added to and removed from player', () => {
    const captionToKeep = video.videosubtitle_set[0];
    let captionToDelete = makeVideoSubtitle(video.key, 'es');
    let captionToAdd = makeVideoSubtitle(video.key, 'fr');
    video.videosubtitle_set.push(captionToDelete);
    let wrapper = renderPlayer();
    wrapper.instance().player = playerStub;
    wrapper.instance().updateSubtitles();
    assert.equal(wrapper.instance().player.tracks.length, 2);
    assert.equal(wrapper.instance().player.tracks[0].src,  makeVideoSubtitleUrl(captionToKeep));
    assert.equal(wrapper.instance().player.tracks[1].src,  makeVideoSubtitleUrl(captionToDelete));
    video.videosubtitle_set = [captionToKeep, captionToAdd];
    wrapper.instance().updateSubtitles();
    assert.equal(wrapper.instance().player.tracks.length, 2);
    assert.equal(wrapper.instance().player.tracks[0].src,  makeVideoSubtitleUrl(captionToKeep));
    assert.equal(wrapper.instance().player.tracks[1].src,  makeVideoSubtitleUrl(captionToAdd));
  });

  it('has a playback speed button on the control bar', () => {
    let wrapper = renderPlayer();
    assert.isDefined(wrapper.find('.vjs-playback-rate-value'));
  });
});
