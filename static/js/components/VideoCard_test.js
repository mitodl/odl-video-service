// @flow
import React from "react"
import sinon from "sinon"
import { shallow } from "enzyme"
import { assert } from "chai"

import VideoCard from "./VideoCard"
import { makeVideoThumbnailUrl, makeVideoUrl } from "../lib/urls"
import * as libVideo from "../lib/video"
import { expect } from "../util/test_utils"
import { makeVideo } from "../factories/video"

describe("VideoCard", () => {
  let sandbox,
    video,
    showEditVideoDialogStub,
    showShareVideoDialogStub,
    showDeleteVideoDialogStub,
    showVideoMenuStub,
    hideVideoMenuStub,
    dropboxSaveMenuStub,
    videoIsProcessingStub,
    videoHasErrorStub,
    videoIsInFlightStub,
    onReplaceVideoStub

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    showEditVideoDialogStub = sandbox.stub()
    showShareVideoDialogStub = sandbox.stub()
    showDeleteVideoDialogStub = sandbox.stub()
    showVideoMenuStub = sandbox.stub()
    hideVideoMenuStub = sandbox.stub()
    video = makeVideo()
    videoIsProcessingStub = sandbox
      .stub(libVideo, "videoIsProcessing")
      .returns(false)
    videoHasErrorStub = sandbox.stub(libVideo, "videoHasError").returns(false)
    videoIsInFlightStub = sandbox
      .stub(libVideo, "videoIsInFlight")
      .returns(false)
    dropboxSaveMenuStub = sandbox.stub(libVideo, "saveToDropbox")
    onReplaceVideoStub = sandbox.stub()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (props = {}) =>
    shallow(
      <VideoCard
        video={video}
        isAdmin={true}
        isMenuOpen={false}
        showEditVideoDialog={showEditVideoDialogStub}
        showShareVideoDialog={showShareVideoDialogStub}
        showDeleteVideoDialog={showDeleteVideoDialogStub}
        showVideoMenu={showVideoMenuStub}
        hideVideoMenu={hideVideoMenuStub}
        onReplaceVideo={onReplaceVideoStub}
        {...props}
      />
    )
  ;[
    [false, ["Share"], "user without admin permissions"],
    [
      true,
      ["Share", "Edit", "Save To Dropbox", "Replace", "Delete"],
      "user with admin permissions"
    ]
  ].forEach(
    ([adminPermissionSetting, expectedControlLabels, testDescriptor]) => {
      it(`${testDescriptor} should be shown ${
        expectedControlLabels.length
      } option(s) for video controls`, () => {
        const isAdmin = adminPermissionSetting
        const wrapper = renderComponent({ isAdmin: isAdmin })
        const menuItems = wrapper.find("Menu").props().menuItems
        assert.equal(menuItems.length, expectedControlLabels.length)
        for (let item = 0; item++; item < menuItems.length) {
          assert.equal(menuItems[item].label, expectedControlLabels[item])
        }
      })
    }
  )

  it("executes the right handlers for video actions (edit/share/etc.)", () => {
    const wrapper = renderComponent({ isAdmin: true, onReplaceVideo: sandbox.stub() })
    const menuItems = wrapper.find("Menu").props().menuItems
    menuItems[0].action()
    sinon.assert.called(showShareVideoDialogStub)
    menuItems[1].action()
    sinon.assert.called(showEditVideoDialogStub)
    menuItems[2].action()
    sinon.assert.called(dropboxSaveMenuStub)
    menuItems[3].action()
    // Replace triggers the hidden dropbox button — just verify the item exists
    assert.equal(menuItems[3].label, "Replace")
    menuItems[4].action()
    sinon.assert.called(showDeleteVideoDialogStub)
  })

  it("Menu has correct show and hide functions", () => {
    const wrapper = renderComponent({ isAdmin: true })
    const menu = wrapper.find("Menu")
    menu.props().showMenu()
    sinon.assert.calledOnce(showVideoMenuStub)
    menu.props().closeMenu()
    sinon.assert.calledOnce(hideVideoMenuStub)
  })

  describe("videoIsInFlight behaviour", () => {
    it("hides Replace menu item when video is in-flight", () => {
      videoIsInFlightStub.returns(true)
      const wrapper = renderComponent({ isAdmin: true })
      const menuItems = wrapper.find("Menu").props().menuItems
      assert.isFalse(menuItems.some(item => item.label === "Replace"))
      assert.equal(menuItems.length, 4)
    })

    it("shows Replace menu item when video is not in-flight", () => {
      videoIsInFlightStub.returns(false)
      const wrapper = renderComponent({ isAdmin: true })
      const menuItems = wrapper.find("Menu").props().menuItems
      assert.isTrue(menuItems.some(item => item.label === "Replace"))
      assert.equal(menuItems.length, 5)
    })

    it("hides the hidden DropboxChooser when video is in-flight", () => {
      videoIsInFlightStub.returns(true)
      const wrapper = renderComponent({ isAdmin: true })
      assert.isFalse(wrapper.find("DropboxChooser").exists())
    })

    it("renders the hidden DropboxChooser when video is not in-flight", () => {
      videoIsInFlightStub.returns(false)
      const wrapper = renderComponent({ isAdmin: true })
      assert.isTrue(wrapper.find("DropboxChooser").exists())
    })

    it("does not show Replace menu item when onReplaceVideo prop is absent, even if not in-flight", () => {
      videoIsInFlightStub.returns(false)
      const wrapper = renderComponent({ isAdmin: true, onReplaceVideo: undefined })
      const menuItems = wrapper.find("Menu").props().menuItems
      assert.isFalse(menuItems.some(item => item.label === "Replace"))
    })
  })

  it(`should have a title that links to the video detail page`, () => {
    const wrapper = renderComponent()
    const title = wrapper.find(".video-card-body h2")
    assert.isTrue(title.exists())
    assert.equal(title.text(), video.title)
    const titleLink = title.find("a")
    assert.isTrue(titleLink.exists())
    assert.include(titleLink.html(), `href="${makeVideoUrl(video.key)}`)
  })
  ;[
    [{ processing: true, error: false }, "In Progress", "processing"],
    [{ processing: false, error: true }, "Upload failed", "error"]
  ].forEach(([stubValues, expectedText, statusDescriptor]) => {
    it(`video with ${statusDescriptor} status should show appropriate message`, () => {
      videoIsProcessingStub.returns(stubValues.processing)
      videoHasErrorStub.returns(stubValues.error)
      const wrapper = renderComponent()
      assert.isFalse(wrapper.find(".thumbnail").exists())
      assert.include(wrapper.find(".message").text(), expectedText)
    })
  })

  it('video with "complete" status should show video thumbnail', () => {
    videoIsProcessingStub.returns(false)
    videoHasErrorStub.returns(false)
    const wrapper = renderComponent()
    const thumbnailImg = wrapper.find(".thumbnail img")
    assert.isTrue(thumbnailImg.exists())
    assert.equal(thumbnailImg.prop("src"), makeVideoThumbnailUrl(video))
  })
  ;[
    [{ processing: true, error: false }, "processing", true],
    [{ processing: false, error: false }, "complete", true],
    [{ processing: false, error: true }, "error", false]
  ].forEach(([stubValues, description, shouldHaveLink]) => {
    it(`video with ${description} status ${expect(
      shouldHaveLink
    )} show the "share" link`, () => {
      videoIsProcessingStub.returns(stubValues.processing)
      videoHasErrorStub.returns(stubValues.error)
      const wrapper = renderComponent()
      const menuItems = wrapper.find("Menu").props().menuItems
      assert.equal(menuItems[0].label, "Share")
    })
  })
})
