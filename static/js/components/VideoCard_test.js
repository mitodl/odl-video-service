// @flow
import React from 'react';
import sinon from 'sinon';
import { shallow } from 'enzyme';
import { assert } from 'chai';

import VideoCard from './VideoCard';
import { makeVideoThumbnailUrl } from "../lib/urls";
import * as libVideo from "../lib/video";
import { expect } from "../util/test_utils";
import { makeVideo } from "../factories/video";

describe('VideoCard', () => {
  let sandbox, video, showEditDialogStub, showShareDialogStub,
    videoIsProcessingStub, videoHasErrorStub;

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    showEditDialogStub = sandbox.stub();
    showShareDialogStub = sandbox.stub();
    video = makeVideo();
    videoIsProcessingStub = sandbox.stub(libVideo, 'videoIsProcessing').returns(false);
    videoHasErrorStub = sandbox.stub(libVideo, 'videoHasError').returns(false);
  });

  afterEach(() => {
    sandbox.restore();
  });

  const renderComponent = (props = {}) => (
    shallow(
      <VideoCard
        video={video}
        isAdmin={true}
        showEditDialog={showEditDialogStub}
        showShareDialog={showShareDialogStub}
        { ...props }
      />
    )
  );

  [
    [false, false, 'user without admin permissions'],
    [true, true, 'user with admin permissions']
  ].forEach(([adminPermissionSetting, shouldShow, testDescriptor]) => {
    it(`video controls ${expect(shouldShow)} be shown for ${testDescriptor}`, () => {
      let isAdmin = adminPermissionSetting;
      let wrapper = renderComponent({isAdmin: isAdmin});
      assert.equal(wrapper.find(".actions a.edit-link").exists(), shouldShow);
    });
  });

  it('handles an edit button and share button click', () => {
    let wrapper = renderComponent({isAdmin: true});
    wrapper.find(".actions a.edit-link").prop('onClick')();
    sinon.assert.called(showEditDialogStub);
    wrapper.find(".actions a.share-link").prop('onClick')();
    sinon.assert.called(showShareDialogStub);
  });

  [
    [{processing: true, error: false}, "In Progress", "processing"],
    [{processing: false, error: true}, "Upload failed", "error", ]
  ].forEach(([stubValues, expectedText, statusDescriptor]) => {
    it(`video with ${statusDescriptor} status should show appropriate message`, () => {
      videoIsProcessingStub.returns(stubValues.processing);
      videoHasErrorStub.returns(stubValues.error);
      let wrapper = renderComponent();
      assert.isFalse(wrapper.find(".thumbnail").exists());
      assert.include(wrapper.find(".message").text(), expectedText);
    });
  });

  it('video with "complete" status should show video thumbnail', () => {
    videoIsProcessingStub.returns(false);
    videoHasErrorStub.returns(false);
    let wrapper = renderComponent();
    let thumbnailImg = wrapper.find(".thumbnail img");
    assert.isTrue(thumbnailImg.exists());
    assert.equal(thumbnailImg.prop('src'), makeVideoThumbnailUrl(video));
  });

  [
    [{processing: true, error: false}, 'processing', true],
    [{processing: false, error: false}, 'complete', true],
    [{processing: false, error: true}, 'error', false],
  ].forEach(([stubValues, description, shouldHaveLink]) => {
    it(`video with ${description} status ${expect(shouldHaveLink)} link to the video page in the title`, () => {
      videoIsProcessingStub.returns(stubValues.processing);
      videoHasErrorStub.returns(stubValues.error);
      let wrapper = renderComponent();
      let title = wrapper.find(".video-card-body h4");
      assert.isTrue(title.exists());
      assert.equal(title.text(), video.title);
      assert.equal(title.find('a').exists(), shouldHaveLink);
    });
  });

  [
    [{processing: true, error: false}, 'processing', true],
    [{processing: false, error: false}, 'complete', true],
    [{processing: false, error: true}, 'error', false],
  ].forEach(([stubValues, description, shouldHaveLink]) => {
    it(`video with ${description} status ${expect(shouldHaveLink)} show the "share" link`, () => {
      videoIsProcessingStub.returns(stubValues.processing);
      videoHasErrorStub.returns(stubValues.error);
      let wrapper = renderComponent();
      assert.equal(wrapper.find(".share-link").exists(), shouldHaveLink);
    });
  });
});
