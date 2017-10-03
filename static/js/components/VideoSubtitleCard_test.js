// @flow
import React from "react";
import sinon from "sinon";
import { shallow } from "enzyme";
import { assert } from "chai";

import { makeVideoSubtitleUrl } from "../lib/urls";
import { expect } from "../util/test_utils";
import { makeVideo } from "../factories/video";
import VideoSubtitleCard from "./VideoSubtitleCard";

describe("VideoSubtitleCard", () => {
  let sandbox, video, uploadStub, deleteStub;

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    uploadStub = sandbox.stub();
    deleteStub = sandbox.stub();
    video = makeVideo();
  });

  afterEach(() => {
    sandbox.restore();
  });

  const renderComponent = (props = {}) => (
    shallow(
      <VideoSubtitleCard
        video={video}
        isAdmin={true}
        uploadVideoSubtitle={uploadStub}
        deleteVideoSubtitle={deleteStub}
        { ...props }
      />
    )
  );

  [
    [false, false, "user without admin permissions"],
    [true, true, "user with admin permissions"]
  ].forEach(([adminPermissionSetting, shouldShow, testDescriptor]) => {
    it(`delete subtitle button ${expect(shouldShow)} be shown for ${testDescriptor}`, () => {
      let isAdmin = adminPermissionSetting;
      let wrapper = renderComponent({isAdmin: isAdmin});
      assert.equal(wrapper.find(".delete-btn").exists(), shouldShow);
    });
  });

  it("handles a delete button and upload button click", () => {
    let wrapper = renderComponent({isAdmin: true});
    wrapper.find(".delete-btn").prop("onClick")();
    sinon.assert.called(deleteStub);
    wrapper.find("#video-subtitle").prop("onChange")();
    sinon.assert.called(uploadStub);
  });

  it("displays the correct download link", () => {
    let wrapper = renderComponent();
    assert.equal(wrapper.find(".download-link").prop("href"), makeVideoSubtitleUrl(video.videosubtitle_set[0]));
  });
});
