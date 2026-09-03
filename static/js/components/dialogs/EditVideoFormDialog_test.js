// @flow
/* global SETTINGS: false */
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { screen, fireEvent, waitFor } from "@testing-library/react"
import configureTestStore from "redux-asserts"
import _ from "lodash"

import EditVideoFormDialog from "./EditVideoFormDialog"

import rootReducer from "../../reducers"
import { actions } from "../../actions"
import * as videoUiActions from "../../actions/videoUi"
import * as toastActions from "../../actions/toast"
import { setSelectedVideoKey } from "../../actions/collectionUi"
import { INITIAL_UI_STATE } from "../../reducers/videoUi"
import * as api from "../../lib/api"
import { makeVideo } from "../../factories/video"
import { makeCollection } from "../../factories/collection"
import renderWithProviders from "../../testUtils/renderWithProviders"
import {
  PERM_CHOICE_LISTS,
  PERM_CHOICE_LOGGED_IN,
  PERM_CHOICE_NONE,
  PERM_CHOICE_OVERRIDE
} from "../../lib/dialog"

const {
  CLEAR_VIDEO_FORM,
  INIT_EDIT_VIDEO_FORM,
  SET_EDIT_VIDEO_TITLE,
  SET_EDIT_VIDEO_DESC,
  SET_VIEW_CHOICE,
  SET_VIEW_LISTS,
  SET_PERM_OVERRIDE_CHOICE,
  SET_VIDEO_FORM_ERRORS
} = videoUiActions.constants

const {
  initEditVideoForm,
  setEditVideoTitle,
  setEditVideoDesc,
  setViewLists,
  setViewChoice,
  setPermOverrideChoice
} = videoUiActions.actionCreators

describe("EditVideoFormDialog", () => {
  let sandbox,
    store,
    listenForActions,
    hideDialogStub,
    video,
    originalEnableVideoPermissions

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    hideDialogStub = sandbox.stub()
    video = makeVideo()
    // Hygiene fix (test-file-only, not a production change): this file
    // mutates the global SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS flag
    // directly in most tests below with no reset, which is a latent
    // cross-test/cross-file leak (flagged in the conversion dossier). Save
    // and restore it so this file can't affect any other spec file's
    // assumed default.
    originalEnableVideoPermissions = SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS
  })

  afterEach(() => {
    sandbox.restore()
    SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS = originalEnableVideoPermissions
  })

  const renderComponent = (props = {}) => {
    return renderWithProviders(
      <EditVideoFormDialog
        open={true}
        hideDialog={hideDialogStub}
        video={video}
        videoUi={INITIAL_UI_STATE}
        {...props}
      />,
      { store }
    )
  }

  it("initializes the form when given a video that doesn't match the current form key", async () => {
    store.dispatch(initEditVideoForm({ key: "mismatching-key" }))
    const previousFormState = store.getState().videoUi.editVideoForm
    await listenForActions([INIT_EDIT_VIDEO_FORM], () => {
      renderComponent()
    })

    assert.notEqual(
      previousFormState.key,
      store.getState().videoUi.editVideoForm.key
    )
    assert.equal(screen.getByLabelText("Title").value, video.title)
    // The description is a rich-text editor: it holds its document in a
    // contenteditable element, so there is no `value` to read.
    await waitFor(() =>
      assert.include(
        document.querySelector("#video-description .ProseMirror").innerHTML,
        video.description
      )
    )
  })

  it("doesn't re-initialize the form when given a video that matches the current form key", () => {
    store.dispatch(initEditVideoForm({ key: video.key }))
    const previousFormState = store.getState().videoUi.editVideoForm
    renderComponent()
    assert.deepEqual(previousFormState, store.getState().videoUi.editVideoForm)
  })

  // eslint-disable-next-line no-unused-vars
  for (const [selector, prop, actionType, newValue, labelText, interaction] of [
    [
      "#video-title",
      "title",
      SET_EDIT_VIDEO_TITLE,
      "new title",
      "Title",
      "change"
    ],
    ["#view-moira-input", "viewLists", SET_VIEW_LISTS, "a,b,c", null, "change"],
    [
      "#video-view-perms-override-view-collection-override",
      "overrideChoice",
      SET_PERM_OVERRIDE_CHOICE,
      PERM_CHOICE_OVERRIDE,
      "Override collection permissions for this video",
      "click"
    ],
    [
      "#video-view-perms-view-only-me",
      "viewChoice",
      SET_VIEW_CHOICE,
      PERM_CHOICE_NONE,
      "Only you and other admins",
      "click"
    ],
    [
      "#video-view-perms-view-logged-in-only",
      "viewChoice",
      SET_VIEW_CHOICE,
      PERM_CHOICE_LOGGED_IN,
      "MIT Touchstone",
      "click"
    ]
  ]) {
    it(`sets ${prop}`, async () => {
      SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS = true
      renderComponent()
      // "view-only-me"/"view-logged-in-only" radios are rendered HTML
      // `disabled` on a fresh mount (defaultPerms is true until an override
      // choice is made -- see EditVideoFormDialog.js's renderPermissions).
      // `fireEvent.click` dispatches a MouseEvent via `dispatchEvent`, which
      // bypasses the browser's disabled-control activation gate -- unlike a
      // real user click (`element.click()`), which does NOT fire on a
      // disabled control. So these two rows must first drive the always-
      // enabled override radio to PERM_CHOICE_OVERRIDE (a real user
      // interaction), which is what actually removes the `disabled`
      // attribute, before touching the target radio -- matching what a real
      // user can do, and proven reachable below via an explicit
      // not-disabled assertion.
      if (
        selector === "#video-view-perms-view-only-me" ||
        selector === "#video-view-perms-view-logged-in-only"
      ) {
        fireEvent.click(
          screen.getByLabelText(
            "Override collection permissions for this video"
          )
        )
      }
      const target = labelText ?
        screen.getByLabelText(labelText) :
        document.querySelector(selector)
      if (interaction === "click") {
        assert.isFalse(
          target.disabled,
          `${selector} must not be disabled before a user can click it`
        )
      }
      const state = await listenForActions([actionType], () => {
        if (interaction === "click") {
          fireEvent.click(target)
        } else {
          fireEvent.change(target, { target: { value: newValue } })
        }
      })
      assert.equal(state.videoUi.editVideoForm[prop], newValue)
    })
  }

  /*
   * Description is not in the table above: it is a rich-text editor, not a
   * form field. It keeps its document in a contenteditable element and reports
   * serialized HTML through onChange, so there is no value for
   * fireEvent.change to set. Driving it the way an author does - through a
   * toolbar control - is what exercises the wiring.
   */
  describe("description", () => {
    const editor = () =>
      document.querySelector("#video-description .ProseMirror")

    // The editor engine is a split chunk, so it arrives after mount.
    const renderWithEditor = async (props = {}) => {
      const result = renderComponent(props)
      await waitFor(() => assert.isNotNull(editor()))
      return result
    }

    it("stores what the editor reports, as HTML", async () => {
      await renderWithEditor()
      const state = await listenForActions([SET_EDIT_VIDEO_DESC], () => {
        fireEvent.click(screen.getByRole("button", { name: "Bulleted list" }))
      })
      assert.include(state.videoUi.editVideoForm.description, "<ul>")
    })

    it("shows the stored description as markup", async () => {
      video.description = "<p>stored <em>text</em></p>"
      await renderWithEditor()
      await waitFor(() => assert.include(editor().innerHTML, "<em>text</em>"))
    })
  })

  // eslint-disable-next-line no-unused-vars
  for (const selector of [
    "#view-moira-input",
    "#video-view-perms-override-view-collection-override",
    "#video-view-perms-view-public",
    "#video-view-perms-view-only-me",
    "#video-view-perms-view-logged-in-only"
  ]) {
    it(`permissions field ${selector} not present if feature is disabled`, () => {
      SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS = false
      // Note: "#video-view-perms-view-public" is absent from every render
      // in this file regardless of the feature flag, because
      // renderComponent() never passes a `collection` prop with
      // `is_public: true` (collectionIsPublic is always falsy here) -- this
      // assertion still validly proves absence, it just isn't proof that
      // the feature flag specifically controls *that* radio's visibility.
      const { container } = renderComponent()
      assert.isNull(container.querySelector(selector))
    })
  }

  it(`updates the video when form is submitted and video permissions are disabled`, async () => {
    SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS = false
    const updateVideoStub = sandbox
      .stub(api, "updateVideo")
      .returns(Promise.resolve(video))
    await listenForActions([INIT_EDIT_VIDEO_FORM], () => {
      renderComponent()
    })
    // set title and description, check the values that updateVideoStub is called with
    const newValues = {
      title:       "New Title",
      description: "New Description"
    }
    store.dispatch(setEditVideoTitle(newValues.title))
    store.dispatch(setEditVideoDesc(newValues.description))
    // Real click on the "Save Changes" button, replacing the old
    // `.find("Dialog").prop("onAccept")()` call. Spiked empirically (see
    // task-5-report.md, Spike A): EditVideoFormDialog renders its Dialog
    // with validateOnClick={true}, so Dialog.js omits the
    // "mdc-dialog__footer__button--accept" class from the button; MDCDialog's
    // foundation only emits "MDCDialog:accept" (and thus only re-invokes
    // onAccept a second time) for a click that lands on an element carrying
    // that exact class (see @material/dialog's ACCEPT_BTN/ACCEPT_SELECTOR
    // constants), so a real click here fires onAccept exactly once, through
    // the Button's plain onClick alone -- confirmed by counting
    // api.updateVideo's call count after a single click.
    //
    // The former `sandbox.stub(wrapper.find("EditVideoFormDialog").instance(),
    // "addToastMessage")` is dropped (see the file's own "adds toast message
    // on submit" test below, which already proves this pattern): instead of
    // stubbing out the trailing addToastMessage/onClose chain, this awaits
    // it in full so nothing keeps dispatching after RTL's automatic
    // unmount.
    await listenForActions(
      [
        actions.videos.patch.requestType,
        actions.videos.patch.successType,
        INIT_EDIT_VIDEO_FORM,
        toastActions.constants.ADD_MESSAGE,
        CLEAR_VIDEO_FORM,
        INIT_EDIT_VIDEO_FORM
      ],
      () => {
        fireEvent.click(screen.getByRole("button", { name: "Save Changes" }))
      }
    )

    sinon.assert.calledWith(updateVideoStub, video.key, newValues)
  })

  it(`updates the video when form is submitted and video permissions are enabled`, async () => {
    SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS = true
    const updateVideoStub = sandbox
      .stub(api, "updateVideo")
      .returns(Promise.resolve(video))
    await listenForActions([INIT_EDIT_VIDEO_FORM], () => {
      renderComponent()
    })
    // set permission override & view choices, check the values that updateVideoStub is called with
    const newValues = {
      title:             "New Title",
      description:       "New Description",
      is_public:         false,
      is_private:        false,
      is_logged_in_only: false,
      view_lists:        ["my-moira-list1", "my-moira-list2"]
    }
    store.dispatch(setEditVideoTitle(newValues.title))
    store.dispatch(setEditVideoDesc(newValues.description))
    store.dispatch(setPermOverrideChoice(PERM_CHOICE_OVERRIDE))
    store.dispatch(setViewChoice(PERM_CHOICE_LISTS))
    store.dispatch(setViewLists(_.map(newValues.view_lists).join(",")))

    // See the previous test for the click/onAccept and full-chain-await
    // rationale (both apply identically here).
    await listenForActions(
      [
        actions.videos.patch.requestType,
        actions.videos.patch.successType,
        INIT_EDIT_VIDEO_FORM,
        toastActions.constants.ADD_MESSAGE,
        CLEAR_VIDEO_FORM,
        INIT_EDIT_VIDEO_FORM
      ],
      () => {
        fireEvent.click(screen.getByRole("button", { name: "Save Changes" }))
      }
    )

    sinon.assert.calledWith(updateVideoStub, video.key, newValues)
  })

  it(`adds toast message on submit`, async () => {
    sandbox.stub(api, "updateVideo").returns(Promise.resolve(video))
    await listenForActions([INIT_EDIT_VIDEO_FORM], () => {
      renderComponent()
    })
    await listenForActions(
      [
        actions.videos.patch.requestType,
        actions.videos.patch.successType,
        INIT_EDIT_VIDEO_FORM,
        toastActions.constants.ADD_MESSAGE,
        CLEAR_VIDEO_FORM,
        INIT_EDIT_VIDEO_FORM
      ],
      () => {
        fireEvent.click(screen.getByRole("button", { name: "Save Changes" }))
      }
    )
    assert.deepEqual(store.getState().toast.messages, [
      {
        key:     "video-saved",
        content: "Changes saved",
        icon:    "check"
      }
    ])
  })

  it("stores form submission errors in state", async () => {
    renderComponent()
    const expectedErrorMessage = "Failed to parse URL from /api/v0/"
    const expectedActionTypes = [
      actions.videos.patch.requestType,
      "RECEIVE_PATCH_VIDEOS_FAILURE",
      SET_VIDEO_FORM_ERRORS
    ]
    // Note: this assertion's error text ("Failed to parse URL from
    // /api/v0/") is a jsdom/node `fetch` implementation detail (no
    // api.updateVideo stub here, so the real fetch runs against a relative
    // URL and rejects), not application logic -- pre-existing fragility
    // carried over unchanged from the Enzyme version, flagged in case it
    // needs updating if the fetch polyfill ever changes.
    await listenForActions(expectedActionTypes, () => {
      fireEvent.click(screen.getByRole("button", { name: "Save Changes" }))
    })
    const actualError = store.getState().videoUi.errors
    assert.include(actualError.message, expectedErrorMessage)
  })

  it("can get a video from the collection state when no video is provided to the component directly", async () => {
    const collection = makeCollection()
    const collectionVideo = collection.videos[0]
    store.dispatch(setSelectedVideoKey(collectionVideo.key))

    // `video`/`shouldUpdateCollection` are connect()-injected props on the
    // unconnected class, which isn't named-exported and can't be
    // introspected directly under RTL. Both facts are re-expressed as
    // observable behavior instead (see task-5-report.md / conversion
    // dossier): which video mapStateToProps picked is proven by the
    // rendered Title input; shouldUpdateCollection's only effect is
    // submitForm's `dispatch(actions.collections.get(video.collection_key))`,
    // observed here by stubbing that action creator directly (so no real
    // network call is made and no extra request/success actions need to be
    // awaited).
    await listenForActions([INIT_EDIT_VIDEO_FORM], () => {
      renderComponent({ video: null, collection })
    })
    assert.equal(screen.getByLabelText("Title").value, collectionVideo.title)

    sandbox.stub(api, "updateVideo").returns(Promise.resolve(collectionVideo))
    const collectionsGetStub = sandbox
      .stub(actions.collections, "get")
      .returns({ type: "NOOP" })

    await listenForActions(
      [
        actions.videos.patch.requestType,
        actions.videos.patch.successType,
        INIT_EDIT_VIDEO_FORM,
        "NOOP",
        toastActions.constants.ADD_MESSAGE,
        CLEAR_VIDEO_FORM,
        INIT_EDIT_VIDEO_FORM
      ],
      () => {
        fireEvent.click(screen.getByRole("button", { name: "Save Changes" }))
      }
    )
    sinon.assert.calledWith(collectionsGetStub, collectionVideo.collection_key)
  })

  it("prefers a video provided via props over a video in a collection", async () => {
    const collection = makeCollection()

    await listenForActions([INIT_EDIT_VIDEO_FORM], () => {
      renderComponent({ video, collection })
    })
    assert.equal(screen.getByLabelText("Title").value, video.title)

    // shouldUpdateCollection === false here (an explicit `video` prop wins
    // over `collection` in mapStateToProps) -- proven by observing that
    // submitting never calls actions.collections.get.
    sandbox.stub(api, "updateVideo").returns(Promise.resolve(video))
    const collectionsGetStub = sandbox
      .stub(actions.collections, "get")
      .returns({ type: "NOOP" })

    await listenForActions(
      [
        actions.videos.patch.requestType,
        actions.videos.patch.successType,
        INIT_EDIT_VIDEO_FORM,
        toastActions.constants.ADD_MESSAGE,
        CLEAR_VIDEO_FORM,
        INIT_EDIT_VIDEO_FORM
      ],
      () => {
        fireEvent.click(screen.getByRole("button", { name: "Save Changes" }))
      }
    )
    sinon.assert.notCalled(collectionsGetStub)
  })
})
