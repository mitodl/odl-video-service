// @flow
import React from "react"
import _ from "lodash"
import { shallow } from "enzyme"
import { assert } from "chai"
import sinon from "sinon"

import { DeleteVideoDialog, mapStateToProps } from "./DeleteVideoDialog"

import { makeCollection } from "../../factories/collection"
import { actions } from "../../actions"

describe("DeleteVideoDialogTests", () => {
  let sandbox, collection, video
  const noop = () => null

  beforeEach(() => {
    collection = makeCollection()
    video = collection.videos[0]
    sandbox = sinon.sandbox.create()
  })

  afterEach(() => {
    sandbox.restore()
  })

  describe("mapStateToProps", () => {
    let state, ownProps

    describe("when ownProps has video", () => {
      beforeEach(() => {
        state = { collectionUi: { selectedVideoKey: video.key } }
        ownProps = { video }
      })

      it("returns expected props", () => {
        const actualProps = mapStateToProps(state, ownProps)
        const expectedProps = { video, shouldUpdateCollection: false }
        assert.deepEqual(actualProps, expectedProps)
      })
    })

    describe("when ownProps has collection", () => {
      beforeEach(() => {
        state = { collectionUi: { selectedVideoKey: video.key } }
        ownProps = { collection }
      })

      it("returns expected props", () => {
        const expectedProps = { video, shouldUpdateCollection: true }
        const actualProps = mapStateToProps(state, ownProps)
        assert.deepEqual(actualProps, expectedProps)
      })
    })
  })

  describe("DeleteVideoDialog Component", () => {
    const renderComponent = (extraProps = {}) => {
      const defaultProps = {
        hideDialog: noop,
        open:       true,
        video
      }
      return shallow(
        <DeleteVideoDialog {...{ ...defaultProps, ...extraProps }} />
      )
    }

    describe("when there is no video", () => {
      let wrapper

      beforeEach(() => {
        wrapper = renderComponent({ video: undefined })
      })

      it("renders nothing", () => {
        assert.equal(wrapper.get(0), null)
      })
    })

    describe("when there is a video", () => {
      let wrapper, instance

      beforeEach(() => {
        wrapper = renderComponent()
        instance = wrapper.instance()
      })

      it("renders Dialog", () => {
        const dialogEl = wrapper.find("Dialog")
        const expectedDialogProps = {
          title:      "Delete Video",
          id:         "delete-video-dialog",
          cancelText: "Cancel",
          submitText: "Yes, Delete",
          open:       instance.props.open,
          hideDialog: instance.props.hideDialog,
          onAccept:   instance.confirmDeletion
        }
        assert.deepEqual(
          _.omit(dialogEl.props(), ["children"]),
          expectedDialogProps
        )
        assert.equal(dialogEl.find("h5").text(), instance.props.video.title)
      })
    })

    describe("confirmDeletion", () => {
      let wrapper, stubs

      beforeEach(async () => {
        const promises = {
          videosDelete: Promise.resolve()
        }
        stubs = {
          dispatch:     sandbox.stub(),
          videosDelete: sandbox
            .stub(actions.videos, "delete")
            .returns(promises.videosDelete),
          collectionsGet:  sandbox.stub(actions.collections, "get"),
          toastAddMessage: sandbox.stub(actions.toast, "addMessage"),
          window:          { location: { origin: "someOrigin" } }
        }
        await promises.videosDelete
      })

      const renderComponentWithStubs = (extraProps = {}) => {
        const wrapper = renderComponent({
          dispatch: stubs.dispatch,
          ...extraProps
        })
        return wrapper
      }

      const generateCommonConfirmDeletionTests = () => {
        it("dispatches video.delete", () => {
          sinon.assert.calledWith(stubs.videosDelete, video.key)
          sinon.assert.calledWith(
            stubs.dispatch,
            stubs.videosDelete.returnValues[0]
          )
        })

        it("dispatches toast.addMessage", () => {
          const expectedMessage = {
            key:     "video-delete",
            content: `Video "${video.title}" was deleted.`,
            icon:    "check"
          }
          sinon.assert.calledWith(stubs.toastAddMessage, {
            message: expectedMessage
          })
          sinon.assert.calledWith(
            stubs.dispatch,
            stubs.toastAddMessage.returnValues[0]
          )
        })
      }

      describe("when shouldUpdateCollection", () => {
        beforeEach(async () => {
          wrapper = renderComponentWithStubs({
            video,
            shouldUpdateCollection: true
          })
          await wrapper.instance().confirmDeletion()
        })

        generateCommonConfirmDeletionTests()

        it("dispatches collections.get", () => {
          sinon.assert.calledWith(stubs.collectionsGet, video.collection_key)
          sinon.assert.calledWith(
            stubs.dispatch,
            stubs.collectionsGet.returnValues[0]
          )
        })
      })

      describe("when not shouldUpdateCollection", () => {
        beforeEach(async () => {
          wrapper = renderComponentWithStubs({
            video,
            shouldUpdateCollection: false,
            window:                 stubs.window
          })
          await wrapper.instance().confirmDeletion()
        })

        generateCommonConfirmDeletionTests()

        it("assigns window.location", () => {
          const expectedLocation = `someOrigin/collections/${video.collection_key}/`
          assert.equal(stubs.window.location, expectedLocation)
        })
      })
    })
  })
})
