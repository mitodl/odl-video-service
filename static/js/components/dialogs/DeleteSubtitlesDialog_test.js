// @flow
import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { screen, render, fireEvent, waitFor } from "@testing-library/react"
import configureTestStore from "redux-asserts"

import { DeleteSubtitlesDialog, mapStateToProps } from "./DeleteSubtitlesDialog"

import rootReducer from "../../reducers"
import { actions } from "../../actions"
import * as toastActions from "../../actions/toast"
import * as api from "../../lib/api"
import { makeCollection } from "../../factories/collection"
import { makeVideo } from "../../factories/video"
import renderWithProviders from "../../testUtils/renderWithProviders"

describe("DeleteSubtitlesDialogTests", () => {
  let sandbox, collection, video, subtitlesFile

  beforeEach(() => {
    collection = makeCollection()
    video = collection.videos[0]
    subtitlesFile = video.videosubtitle_set[0]
    sandbox = sinon.createSandbox()
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
    const defaultProps = () => ({
      hideDialog: () => {},
      open:       true,
      videoKey:   video.key,
      subtitlesFile
    })

    // This describe is a sibling of (not nested inside) the default-render
    // setup below, so it does not inherit an outer beforeEach that would
    // otherwise leave a whole extra mdc-dialog tree attached to
    // document.body for this test's duration. See the conversion dossier
    // (DeleteDialogs.md) for why the original Enzyme file's nesting was
    // harmless there but worth not carrying forward under a full RTL mount.
    describe("when there is no subtitlesFile", () => {
      it("renders nothing", () => {
        const { container } = render(
          <DeleteSubtitlesDialog
            {...defaultProps()}
            subtitlesFile={undefined}
          />
        )
        assert.equal(container.children.length, 0)
      })
    })

    describe("when there is a subtitlesFile", () => {
      it("renders Dialog", () => {
        const { container } = render(
          <DeleteSubtitlesDialog {...defaultProps()} />
        )

        // Shallow-rendering used to deep-equal the entire props object
        // passed to <Dialog>. A full mount can't introspect React props
        // directly, so this is decomposed into the visible facts the
        // shallow assertion was standing in for: title, the dialog's DOM
        // id, button labels, the subtitles filename text, and open-state
        // (via absence of the "closed" inline style). The
        // `hideDialog`/`onAccept` *identity*-wiring sub-assertions from the
        // old test are intentionally dropped -- see the commit message for
        // why (MDC onAccept double-dispatch makes clicking the submit
        // button unsafe, and there is no real-DOM way to observe "this
        // exact function reference was passed as a prop" without React
        // internals).
        assert.isNotNull(
          screen.getByRole("heading", { name: "Delete Subtitles" })
        )
        const dialogEl = container.querySelector("#delete-subtitles-dialog")
        assert.isNotNull(dialogEl)
        assert.isNotNull(screen.getByRole("button", { name: "Cancel" }))
        assert.isNotNull(screen.getByRole("button", { name: "Yes, Delete" }))
        assert.isNotNull(screen.getByText(subtitlesFile.filename))
        // Closest visible proxy for "open was truthy": Dialog only sets an
        // inline `display: none` style when `open` is falsy.
        assert.isNull(dialogEl.getAttribute("style"))
      })
    })

    describe("accept button wiring", () => {
      let store, deleteSubtitleStub

      beforeEach(() => {
        store = configureTestStore(rootReducer)
        deleteSubtitleStub = sandbox
          .stub(api, "deleteSubtitle")
          .returns(Promise.resolve())
        sandbox
          .stub(api, "getVideo")
          .returns(Promise.resolve(makeVideo(video.key)))
      })

      it("wires the Yes, Delete button to onConfirmDeletion", async () => {
        renderWithProviders(
          <DeleteSubtitlesDialog
            {...defaultProps()}
            dispatch={store.dispatch}
          />,
          { store }
        )

        // Dialog.js's MDCDialog:accept listener AND the submit Button's React
        // onClick both fire onAccept when validateOnClick is absent, so a
        // real click double-dispatches onConfirmDeletion. That is a known,
        // deferred issue (see the commit message / hq#12639 dossier) -- this
        // test asserts `calledWith`, never `calledOnce`, so the double-fire
        // doesn't make it flaky or wrong. This test exists to prove the
        // button is actually WIRED to onConfirmDeletion, which the
        // render-only test above cannot show.
        fireEvent.click(screen.getByRole("button", { name: "Yes, Delete" }))

        await waitFor(() =>
          sinon.assert.calledWith(deleteSubtitleStub, subtitlesFile.id)
        )
      })
    })

    describe("onConfirmDeletion", () => {
      let store,
        listenForActions,
        deleteSubtitleStub,
        getVideoStub,
        dialogInstance

      beforeEach(async () => {
        store = configureTestStore(rootReducer)
        listenForActions = store.createListenForActions()
        deleteSubtitleStub = sandbox
          .stub(api, "deleteSubtitle")
          .returns(Promise.resolve())
        getVideoStub = sandbox
          .stub(api, "getVideo")
          .returns(Promise.resolve(makeVideo(video.key)))

        renderWithProviders(
          <DeleteSubtitlesDialog
            {...defaultProps()}
            dispatch={store.dispatch}
            ref={instance => {
              dialogInstance = instance
            }}
          />,
          { store }
        )

        // Calling onConfirmDeletion directly b/c MDC dialog double-fires
        // onAccept through both the Dialog's MDCDialog:accept listener and
        // the Button's onClick (see commit message / dossier).
        await listenForActions(
          [
            actions.videoSubtitles.delete.requestType,
            actions.videoSubtitles.delete.successType,
            toastActions.constants.ADD_MESSAGE,
            actions.videos.get.requestType,
            actions.videos.get.successType
          ],
          () => dialogInstance.onConfirmDeletion()
        )
      })

      it("dispatches videoSubtitles.delete", () => {
        sinon.assert.calledWith(deleteSubtitleStub, subtitlesFile.id)
      })

      it("dispatches toast.addMessage", () => {
        const expectedMessage = {
          key:     "subtitles-deleted",
          content: "Subtitles file deleted",
          icon:    "check"
        }
        assert.deepInclude(store.getState().toast.messages, expectedMessage)
      })

      it("dispatches getVideo", () => {
        sinon.assert.calledWith(getVideoStub, video.key)
      })
    })
  })
})
