// @flow
import React from 'react';
import sinon from 'sinon';
import { shallow } from 'enzyme';
import { assert } from 'chai';

import VideoCard from './VideoCard';
import { expect } from "../util/test_utils";
import { makeVideo } from "../factories/video";

describe('VideoCard', () => {
  let sandbox, showEditDialogStub, showShareDialogStub, video;

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    showEditDialogStub = sandbox.stub();
    showShareDialogStub = sandbox.stub();
    video = makeVideo();
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
    it(`video controls ${expect(shouldShow)} be shown for ${testDescriptor}`, async () => {
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
});
