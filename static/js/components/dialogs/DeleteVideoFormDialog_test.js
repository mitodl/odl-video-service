// @flow
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { screen } from "@testing-library/react"
import configureTestStore from "redux-asserts"

import ConnectedDeleteVideoDialog, { DeleteVideoDialog } from "./DeleteVideoDialog"

import rootReducer from "../../reducers"
import { actions } from "../../actions"
import { setSelectedVideoKey } from "../../actions/collectionUi"
import * as api from "../../lib/api"
import { makeCollectionUrl } from "../../lib/urls"
import { makeVideo } from "../../factories/video"
import { makeCollection } from "../../factories/collection"
import renderWithProviders from "../../testUtils/renderWithProviders"

describe("DeleteVideoDialog", () => {
  let sandbox, store, listenForActions, hideDialogStub, deleteVideoStub, video

  beforeEach(() => {
    sandbox = sinon.createSandbox()
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
    return renderWithProviders(
      <ConnectedDeleteVideoDialog
        open={true}
        hideDialog={hideDialogStub}
        video={video}
        {...props}
      />,
      { store }
    )
  }

  const renderUnconnectedComponent = (props = {}) => {
    let dialogInstance
    renderWithProviders(
      <DeleteVideoDialog
        open={true}
        hideDialog={hideDialogStub}
        dispatch={store.dispatch}
        shouldUpdateCollection={false}
        video={video}
        {...props}
        ref={(instance) => { dialogInstance = instance }}
      />,
      { store }
    )
    return dialogInstance
  }

  it("updates the video when the form is submitted", async () => {
    const dialogInstance = renderUnconnectedComponent()

    await listenForActions(
      [actions.videos.delete.requestType, actions.videos.delete.successType],
      () => {
        // Calling confirmDeletion directly b/c MDC dialog double-fires onAccept
        // through both the Dialog's MDCDialog:accept listener and the Button's onClick
        dialogInstance.confirmDeletion()
      }
    )

    sinon.assert.calledWith(deleteVideoStub, video.key)
  })

  it("can get a video from the collection state when no video is provided to the component directly", () => {
    const collection = makeCollection()
    const collectionVideo = collection.videos[0]
    store.dispatch(setSelectedVideoKey(collectionVideo.key))
    renderComponent({
      video:      null,
      collection: collection
    })
    // Assert that the correct video from the collection state is displayed
    assert.isNotNull(screen.getByText(collectionVideo.title))
    assert.isNotNull(screen.getByText("Are you sure you want to delete this video?"))
  })

  it("prefers a video provided via props over a video in a collection", () => {
    const collection = makeCollection()
    renderComponent({
      video:      video,
      collection: collection
    })
    // Assert that the video prop is displayed, not the collection video
    assert.isNotNull(screen.getByText(video.title))
    assert.isNotNull(screen.getByText("Are you sure you want to delete this video?"))
  })

  it("should change the browser URL when a video is deleted from the video detail page", async () => {
    const dialogInstance = renderUnconnectedComponent()

    const locationOrigin = window.location.origin
    await listenForActions(
      [actions.videos.delete.requestType, actions.videos.delete.successType],
      () => {
        // Calling confirmDeletion directly b/c MDC dialog double-fires onAccept
        // through both the Dialog's MDCDialog:accept listener and the Button's onClick
        dialogInstance.confirmDeletion()
          .then(() => {
            const collectionUrl = `${makeCollectionUrl(video.collection_key)}`
            assert.isAtLeast(collectionUrl.length, 1)
            assert.equal(window.location, `${locationOrigin}${collectionUrl}`)
          })
      }
    )
  })
})
