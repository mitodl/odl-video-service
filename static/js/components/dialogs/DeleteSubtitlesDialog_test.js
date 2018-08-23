// @flow
import React from "react"
import _ from "lodash"
import { shallow } from "enzyme"
import { assert } from "chai"
import sinon from "sinon"

import { DeleteSubtitlesDialog, mapStateToProps } from "./DeleteSubtitlesDialog"

import { makeCollection } from "../../factories/collection"
import { actions } from "../../actions"

describe("DeleteSubtitlesDialogTests", () => {
  let sandbox, collection, video, subtitlesFile
  const noop = () => null

  beforeEach(() => {
    collection = makeCollection()
    video = collection.videos[0]
    subtitlesFile = video.videosubtitle_set[0]
    sandbox = sinon.sandbox.create()
  })

  afterEach(() => {
    sandbox.restore()
  })

  describe("mapStateToProps", () => {
    let state, actualProps

    beforeEach(() => {
      state = {
        videoUi: {
          currentVideoKey:     video.key,
          currentSubtitlesKey: subtitlesFile.id
        },
        videos: {
          data: new Map([[video.key, video]])
        }
      }
      actualProps = mapStateToProps(state)
    })

    it("passes subtitlesFile", () => {
      assert.deepEqual(actualProps.subtitlesFile, subtitlesFile)
    })

    it("passes videoKey ", () => {
      assert.equal(actualProps.videoKey, video.key)
    })
  })

  describe("DeleteSubtitlesDialog Component", () => {
    let wrapper, instance

    const renderComponent = (extraProps = {}) => {
      const defaultProps = {
        hideDialog: noop,
        open:       true,
        videoKey:   video.key,
        subtitlesFile
      }
      return shallow(
        <DeleteSubtitlesDialog {...{ ...defaultProps, ...extraProps }} />
      )
    }

    beforeEach(() => {
      wrapper = renderComponent()
      instance = wrapper.instance()
    })

    describe("when there is no subtitlesFile", () => {
      beforeEach(() => {
        wrapper = renderComponent({ subtitlesFile: undefined })
      })

      it("renders nothing", () => {
        assert.equal(wrapper.get(0), null)
      })
    })

    it("renders Dialog", () => {
      const dialogEl = wrapper.find("Dialog")
      const expectedDialogProps = {
        title:      "Delete Subtitles",
        id:         "delete-subtitles-dialog",
        cancelText: "Cancel",
        submitText: "Yes, Delete",
        open:       instance.props.open,
        hideDialog: instance.props.hideDialog,
        onAccept:   instance.onConfirmDeletion
      }
      assert.deepEqual(
        _.omit(dialogEl.props(), ["children"]),
        expectedDialogProps
      )
      assert.equal(
        dialogEl.find("h5").text(),
        instance.props.subtitlesFile.filename
      )
    })

    describe("onConfirmDeletion", () => {
      let instance, stubs, promises

      beforeEach(async () => {
        promises = {
          videoSubtitlesDelete: Promise.resolve()
        }
        stubs = {
          dispatch:             sandbox.stub(),
          videoSubtitlesDelete: sandbox
            .stub(actions.videoSubtitles, "delete")
            .returns(promises.videoSubtitlesDelete),
          toastAddMessage: sandbox.stub(actions.toast, "addMessage"),
          videosGet:       sandbox.stub(actions.videos, "get")
        }
        instance = renderComponent({ dispatch: stubs.dispatch }).instance()
        await instance.onConfirmDeletion()
      })

      it("dispatches videoSubtitles.delete", () => {
        sinon.assert.calledWith(
          stubs.videoSubtitlesDelete,
          instance.props.subtitlesFile.id
        )
        sinon.assert.calledWith(
          stubs.dispatch,
          stubs.videoSubtitlesDelete.returnValues[0]
        )
      })

      it("dispatches toast.addMessage", () => {
        const expectedMessage = {
          key:     "subtitles-deleted",
          content: "Subtitles file deleted",
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

      it("dispatches getVideo", () => {
        sinon.assert.calledWith(stubs.videosGet, instance.props.videoKey)
        sinon.assert.calledWith(stubs.dispatch, stubs.videosGet.returnValues[0])
      })
    })
  })
})
