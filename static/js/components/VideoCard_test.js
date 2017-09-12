// @flow
import React from 'react';
import sinon from 'sinon';
import { shallow } from 'enzyme';
import { assert } from 'chai';

import VideoCard from './VideoCard';
import { expect } from "../util/test_utils";
import { makeVideo } from "../factories/video";

describe('VideoCard', () => {
  let sandbox, showDialogStub, video;

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    showDialogStub = sandbox.stub();
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
        showDialog={showDialogStub}
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
      assert.equal(wrapper.find(".actions a").exists(), shouldShow);
    });
  });

  it('handles an edit button click', () => {
    let wrapper = renderComponent({isAdmin: true});
    wrapper.find(".actions a").prop('onClick')();
    sinon.assert.called(showDialogStub);
  });
});
