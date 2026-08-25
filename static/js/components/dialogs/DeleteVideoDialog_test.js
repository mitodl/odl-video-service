// @flow
import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { screen, render, fireEvent, waitFor } from "@testing-library/react"
import configureTestStore from "redux-asserts"

import { DeleteVideoDialog, mapStateToProps } from "./DeleteVideoDialog"

import rootReducer from "../../reducers"
import { actions } from "../../actions"
import * as toastActions from "../../actions/toast"
import * as api from "../../lib/api"
import { makeCollectionUrl } from "../../lib/urls"
import { makeCollection } from "../../factories/collection"
import renderWithProviders from "../../testUtils/renderWithProviders"

describe("DeleteVideoDialogTests", () => {
  let sandbox, collection, video

  beforeEach(() => {
    collection = makeCollection()
    video = collection.videos[0]
    sandbox = sinon.createSandbox()
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
    const defaultProps = () => ({
      hideDialog: () => {},
      open:       true,
      video
    })

    describe("when there is no video", () => {
      it("renders nothing", () => {
        const { container } = render(
          <DeleteVideoDialog {...defaultProps()} video={undefined} />
        )
        assert.equal(container.children.length, 0)
      })
    })

    describe("when there is a video", () => {
      it("renders Dialog", () => {
        const { container } = render(<DeleteVideoDialog {...defaultProps()} />)

        // Shallow-rendering used to deep-equal the entire props object passed
        // to <Dialog>. A full mount can't introspect React props directly, so
        // this is decomposed into the visible facts the shallow assertion was
        // standing in for: title, the dialog's DOM id, button labels, the
        // video title text, and open-state (via absence of the "closed"
        // inline style). The `hideDialog`/`onAccept` *identity*-wiring
        // sub-assertions from the old test are intentionally dropped -- see
        // the commit message for why (MDC onAccept double-dispatch makes
        // clicking the submit button unsafe, and there is no real-DOM way to
        // observe "this exact function reference was passed as a prop"
        // without React internals).
        assert.isNotNull(screen.getByRole("heading", { name: "Delete Video" }))
        const dialogEl = container.querySelector("#delete-video-dialog")
        assert.isNotNull(dialogEl)
        assert.isNotNull(screen.getByRole("button", { name: "Cancel" }))
        assert.isNotNull(screen.getByRole("button", { name: "Yes, Delete" }))
        assert.isNotNull(screen.getByText(video.title))
        // Closest visible proxy for "open was truthy": Dialog only sets an
        // inline `display: none` style when `open` is falsy.
        assert.isNull(dialogEl.getAttribute("style"))
      })
    })

    describe("accept button wiring", () => {
      let store, deleteVideoStub

      beforeEach(() => {
        store = configureTestStore(rootReducer)
        deleteVideoStub = sandbox
          .stub(api, "deleteVideo")
          .returns(Promise.resolve())
        sandbox
          .stub(api, "getCollection")
          .returns(Promise.resolve(makeCollection()))
      })

      it("wires the Yes, Delete button to confirmDeletion", async () => {
        renderWithProviders(
          <DeleteVideoDialog
            {...defaultProps()}
            dispatch={store.dispatch}
            shouldUpdateCollection={true}
          />,
          { store }
        )

        // Dialog.js's MDCDialog:accept listener AND the submit Button's React
        // onClick both fire onAccept when validateOnClick is absent, so a
        // real click double-dispatches confirmDeletion. That is a known,
        // deferred issue (see the commit message / hq#12639 dossier) -- this
        // test asserts `calledWith`, never `calledOnce`, so the double-fire
        // doesn't make it flaky or wrong. This test exists to prove the
        // button is actually WIRED to confirmDeletion, which the render-only
        // test above cannot show.
        fireEvent.click(screen.getByRole("button", { name: "Yes, Delete" }))

        await waitFor(() => sinon.assert.calledWith(deleteVideoStub, video.key))
      })
    })

    describe("confirmDeletion", () => {
      let store, listenForActions, deleteVideoStub, getCollectionStub

      const renderUnconnectedComponent = (props = {}) => {
        let dialogInstance
        renderWithProviders(
          <DeleteVideoDialog
            {...defaultProps()}
            dispatch={store.dispatch}
            {...props}
            ref={instance => {
              dialogInstance = instance
            }}
          />,
          { store }
        )
        return dialogInstance
      }

      beforeEach(() => {
        store = configureTestStore(rootReducer)
        listenForActions = store.createListenForActions()
        deleteVideoStub = sandbox
          .stub(api, "deleteVideo")
          .returns(Promise.resolve())
        getCollectionStub = sandbox
          .stub(api, "getCollection")
          .returns(Promise.resolve(makeCollection()))
      })

      describe("when shouldUpdateCollection", () => {
        beforeEach(async () => {
          const dialogInstance = renderUnconnectedComponent({
            video,
            shouldUpdateCollection: true
          })

          // Calling confirmDeletion directly b/c MDC dialog double-fires
          // onAccept through both the Dialog's MDCDialog:accept listener and
          // the Button's onClick (see commit message / dossier).
          await listenForActions(
            [
              actions.videos.delete.requestType,
              actions.videos.delete.successType,
              toastActions.constants.ADD_MESSAGE,
              actions.collections.get.requestType,
              actions.collections.get.successType
            ],
            () => dialogInstance.confirmDeletion()
          )
        })

        it("dispatches video.delete", () => {
          sinon.assert.calledWith(deleteVideoStub, video.key)
        })

        it("dispatches toast.addMessage", () => {
          const expectedMessage = {
            key:     "video-delete",
            content: `Video "${video.title}" was deleted.`,
            icon:    "check"
          }
          assert.deepInclude(store.getState().toast.messages, expectedMessage)
        })

        it("dispatches collections.get", () => {
          sinon.assert.calledWith(getCollectionStub, video.collection_key)
        })
      })

      describe("when not shouldUpdateCollection", () => {
        let locationOrigin, originalLocationHref

        beforeEach(async () => {
          // Mutates the real global `window.location` (no fake `window` prop
          // passed) -- mirrors the already-merged
          // DeleteVideoFormDialog_test.js's equivalent test, which the
          // conversion dossier verified produces zero stderr both alone and
          // as part of the whole dialogs/ folder run. Capture the origin
          // (and the full href, to restore afterward so this mutation can't
          // leak into later tests/files) before calling confirmDeletion,
          // since the assignment mutates window.location itself.
          originalLocationHref = window.location.href
          locationOrigin = window.location.origin

          const dialogInstance = renderUnconnectedComponent({
            video,
            shouldUpdateCollection: false
          })

          await listenForActions(
            [
              actions.videos.delete.requestType,
              actions.videos.delete.successType,
              toastActions.constants.ADD_MESSAGE
            ],
            () => dialogInstance.confirmDeletion()
          )
        })

        afterEach(() => {
          window.location = originalLocationHref
        })

        it("dispatches video.delete", () => {
          sinon.assert.calledWith(deleteVideoStub, video.key)
        })

        it("dispatches toast.addMessage", () => {
          const expectedMessage = {
            key:     "video-delete",
            content: `Video "${video.title}" was deleted.`,
            icon:    "check"
          }
          assert.deepInclude(store.getState().toast.messages, expectedMessage)
        })

        it("assigns window.location", () => {
          assert.equal(
            window.location,
            `${locationOrigin}${makeCollectionUrl(video.collection_key)}`
          )
        })
      })
    })
  })
})
