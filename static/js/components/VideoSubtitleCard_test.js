// @flow
import React from "react"
import sinon from "sinon"
import { render, fireEvent } from "@testing-library/react"
import { assert } from "chai"

import { makeVideoSubtitleUrl } from "../lib/urls"
import { expect } from "../util/test_utils"
import { makeVideo } from "../factories/video"
import VideoSubtitleCard from "./VideoSubtitleCard"

describe("VideoSubtitleCard", () => {
  let sandbox, video, uploadStub, deleteStub

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    uploadStub = sandbox.stub()
    deleteStub = sandbox.stub()
    video = makeVideo()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (props = {}) =>
    render(
      <VideoSubtitleCard
        video={video}
        isAdmin={true}
        uploadVideoSubtitle={uploadStub}
        deleteVideoSubtitle={deleteStub}
        {...props}
      />
    )
  ;[
    [false, false, "user without admin permissions"],
    [true, true, "user with admin permissions"]
  ].forEach(([adminPermissionSetting, shouldShow, testDescriptor]) => {
    it(`delete subtitle button ${expect(
      shouldShow
    )} be shown for ${testDescriptor}`, () => {
      const isAdmin = adminPermissionSetting
      const { container } = renderComponent({ isAdmin: isAdmin })
      assert.equal(Boolean(container.querySelector(".delete-btn")), shouldShow)
    })
  })

  it("handles a delete button and upload button click", () => {
    const { container } = renderComponent({ isAdmin: true })
    fireEvent.click(container.querySelector(".delete-btn"))
    sinon.assert.called(deleteStub)
    fireEvent.change(container.querySelector("#video-subtitle"))
    sinon.assert.called(uploadStub)
  })

  it("displays the correct download link", () => {
    const { container } = renderComponent()
    assert.equal(
      container.querySelector(".download-link").getAttribute("href"),
      makeVideoSubtitleUrl(video.videosubtitle_set[0])
    )
  })
})
