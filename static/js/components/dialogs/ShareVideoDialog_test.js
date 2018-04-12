// @flow
import React from "react"
import sinon from "sinon"
import { mount } from "enzyme"
import { assert } from "chai"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"

import ShareVideoDialog from "./ShareVideoDialog"

import rootReducer from "../../reducers"
import { setSelectedVideoKey } from "../../actions/collectionUi"
import { makeVideo } from "../../factories/video"
import { SET_SHARE_VIDEO_TIME_ENABLED } from "../../actions/videoUi"

describe("ShareVideoDialog", () => {
  let sandbox, store, hideDialogStub, listenForActions

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    hideDialogStub = sandbox.stub()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (props = {}) => {
    return mount(
      <Provider store={store}>
        <div>
          <ShareVideoDialog
            open={true}
            hideDialog={hideDialogStub}
            {...props}
          />
        </div>
      </Provider>
    )
  }

  it("shows the correct content", async () => {
    const video = makeVideo()
    const wrapper = renderComponent({ video: video })
    assert.equal(
      wrapper
        .find("#video-url")
        .hostNodes()
        .props().value,
      `http://fake/videos/${video.key}/`
    )
    assert.isTrue(
      wrapper
        .find("#video-embed-code")
        .hostNodes()
        .props()
        .value.startsWith(
          `<iframe src="http://fake/videos/${video.key}/embed/"`
        )
    )
  })
  ;[false, true].forEach(function(checked) {
    it("adds time in seconds to the links only if checkbox is checked", async () => {
      const video = makeVideo()
      const wrapper = renderComponent({ video: video })
      await listenForActions([SET_SHARE_VIDEO_TIME_ENABLED], () => {
        // Calling onAccept directly b/c click doesn't work in JS tests due to MDC
        wrapper
          .find("ShareVideoDialog")
          .find("Dialog")
          .find('input[type="checkbox"]')
          .simulate("change", { target: { checked } })
      })
      assert.equal(
        wrapper
          .find("#video-url")
          .hostNodes()
          .props().value,
        `http://fake/videos/${video.key}/${checked ? "?start=0" : ""}`
      )
      assert.isTrue(
        wrapper
          .find("#video-embed-code")
          .hostNodes()
          .props()
          .value.startsWith(
            `<iframe src="http://fake/videos/${video.key}/embed/${
              checked ? "?start=0" : ""
            }"`
          )
      )
    })
  })

  it("gets the video key from a video object provided as a prop", () => {
    const video = makeVideo()
    const wrapper = renderComponent({ video: video })
    assert.equal(wrapper.find("ShareVideoDialog").prop("videoKey"), video.key)
  })

  it("gets the video key from the collection UI state if a video object isn't passed in", () => {
    const videoKey = "video-key"
    store.dispatch(setSelectedVideoKey(videoKey))
    const wrapper = renderComponent({ video: null })
    assert.equal(wrapper.find("ShareVideoDialog").prop("videoKey"), videoKey)
  })
})
