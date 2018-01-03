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

describe("ShareVideoDialog", () => {
  let sandbox, store, hideDialogStub

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
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
      wrapper.find("#video-url").props().value,
      `http://fake/videos/${video.key}/embed/`
    )
    assert.isTrue(
      wrapper
        .find("#video-embed-code")
        .props()
        .value.startsWith(
          `<iframe src="http://fake/videos/${video.key}/embed/"`
        )
    )
  })

  it("gets the video key from a video object provided as a prop", () => {
    let wrapper, video
    video = makeVideo()
    wrapper = renderComponent({ video: video })
    assert.equal(wrapper.find("ShareVideoDialog").prop("videoKey"), video.key)
  })

  it("gets the video key from the collection UI state if a video object isn't passed in", () => {
    let wrapper, videoKey
    videoKey = "video-key"
    store.dispatch(setSelectedVideoKey(videoKey))
    wrapper = renderComponent({ video: null })
    assert.equal(wrapper.find("ShareVideoDialog").prop("videoKey"), videoKey)
  })
})
