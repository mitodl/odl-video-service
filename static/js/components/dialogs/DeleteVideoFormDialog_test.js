// @flow
import React from "react"
import sinon from "sinon"
import { mount } from "enzyme"
import { assert } from "chai"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"

import DeleteVideoDialog from "./DeleteVideoDialog"

import rootReducer from "../../reducers"
import { actions } from "../../actions"
import { setSelectedVideoKey } from "../../actions/collectionUi"
import * as api from "../../lib/api"
import { makeCollectionUrl } from "../../lib/urls"
import { makeVideo } from "../../factories/video"
import { makeCollection } from "../../factories/collection"

describe("DeleteVideoDialog", () => {
  let sandbox, store, listenForActions, hideDialogStub, deleteVideoStub, video

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    hideDialogStub = sandbox.stub()
    deleteVideoStub = sandbox
      .stub(api, "deleteVideo")
      .returns(Promise.resolve())
    video = makeVideo()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (props = {}) => {
    return mount(
      <Provider store={store}>
        <div>
          <DeleteVideoDialog
            open={true}
            hideDialog={hideDialogStub}
            video={video}
            {...props}
          />
        </div>
      </Provider>
    )
  }

  it("updates the video when the form is submitted", async () => {
    const wrapper = renderComponent()
    if (!wrapper) throw new Error("Render failed")

    await listenForActions(
      [actions.videos.delete.requestType, actions.videos.delete.successType],
      () => {
        // Calling onAccept directly b/c click doesn't work in JS tests due to MDC
        wrapper
          .find("DeleteVideoDialog")
          .find("Dialog")
          .prop("onAccept")()
      }
    )

    sinon.assert.calledWith(deleteVideoStub, video.key)
  })

  it("can get a video from the collection state when no video is provided to the component directly", () => {
    const collection = makeCollection()
    const collectionVideo = collection.videos[0]
    store.dispatch(setSelectedVideoKey(collectionVideo.key))
    const wrapper = renderComponent({
      video:      null,
      collection: collection
    })
    const dialogProps = wrapper.find("DeleteVideoDialog").props()
    assert.deepEqual(dialogProps.video, collectionVideo)
    assert.equal(dialogProps.shouldUpdateCollection, true)
  })

  it("prefers a video provided via props over a video in a collection", () => {
    const collection = makeCollection()
    const wrapper = renderComponent({
      video:      video,
      collection: collection
    })
    const dialogProps = wrapper.find("DeleteVideoDialog").props()
    assert.deepEqual(dialogProps.video, video)
    assert.equal(dialogProps.shouldUpdateCollection, false)
  })

  it("should change the browser URL when a video is deleted from the video detail page", async () => {
    const wrapper = renderComponent()
    if (!wrapper) throw new Error("Render failed")

    const locationOrigin = window.location.origin
    await listenForActions(
      [actions.videos.delete.requestType, actions.videos.delete.successType],
      () => {
        // Calling onAccept directly b/c click doesn't work in JS tests due to MDC
        wrapper
          .find("DeleteVideoDialog")
          .find("Dialog")
          .prop("onAccept")()
          .then(() => {
            const collectionUrl = `${makeCollectionUrl(video.collection_key)}`
            assert.isAtLeast(collectionUrl.length, 1)
            assert.equal(window.location, `${locationOrigin}${collectionUrl}`)
          })
      }
    )
  })
})
