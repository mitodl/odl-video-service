// @flow
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { screen, fireEvent, within, waitFor } from "@testing-library/react"
import configureTestStore from "redux-asserts"

import CollectionFormDialog from "./CollectionFormDialog"

import rootReducer from "../../reducers"
import { actions } from "../../actions"
import {
  setAdminChoice,
  setAdminLists,
  setViewChoice,
  setViewLists,
  setCollectionDesc,
  setCollectionTitle,
  setEdxCourseId,
  setOwnerId,
  SET_COLLECTION_TITLE,
  SET_COLLECTION_DESC,
  SET_ADMIN_CHOICE,
  SET_ADMIN_LISTS,
  SET_VIEW_CHOICE,
  SET_VIEW_LISTS,
  SET_OWNER_ID,
  showNewCollectionDialog,
  showEditCollectionDialog,
  CLEAR_COLLECTION_FORM,
  SET_COLLECTION_FORM_ERRORS,
  CLEAR_COLLECTION_ERRORS
} from "../../actions/collectionUi"
import * as toastActions from "../../actions/toast"
import { INITIAL_UI_STATE } from "../../reducers/collectionUi"
import { PERM_CHOICE_LISTS, PERM_CHOICE_NONE } from "../../lib/dialog"
import * as api from "../../lib/api"
import { getCollectionForm } from "../../lib/collection"
import { makeCollection } from "../../factories/collection"
import { makeCollectionUrl } from "../../lib/urls"
import renderWithProviders from "../../testUtils/renderWithProviders"

describe("CollectionFormDialog", () => {
  let sandbox,
    store,
    listenForActions,
    hideDialogStub,
    collection,
    uiState,
    getPotentialCollectionOwnersStub

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    hideDialogStub = sandbox.stub()
    collection = makeCollection()
    uiState = INITIAL_UI_STATE

    // Mock the users API response
    getPotentialCollectionOwnersStub = sandbox
      .stub(api, "getPotentialCollectionOwners")
      .returns(
        Promise.resolve({
          users: [
            { id: 1, username: "user1", email: "user1@example.com" },
            { id: 2, username: "user2", email: "user2@example.com" }
          ]
        })
      )
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (props = {}) =>
    renderWithProviders(
      <CollectionFormDialog
        collectionUi={uiState}
        collection={collection}
        open={true}
        hideDialog={hideDialogStub}
        isEdxCourseAdmin={true}
        collectionKey={"00000000-0000-0000-0000-000000000000"}
        {...props}
      />,
      { store }
    )

  // componentDidMount kicks off the potential-owners fetch, which dispatches
  // a REQUEST action synchronously and a RECEIVE_..._SUCCESS a few
  // microtasks later. redux-asserts' listenForActions matches the cumulative
  // action list as a strict set, so those two actions must be fully drained
  // *before* any listenForActions window opens below -- otherwise they can
  // land inside the window and make it hang or reject. Waiting for the two
  // rendered <option>s is the user-visible signal that the fetch completed;
  // it is also the direct replacement for the old `wrapper.state().users`
  // reads (state.users has exactly one consumer: the Owner <option> list).
  const renderDialog = async (props = {}) => {
    const result = renderComponent(props)
    await waitFor(() => assert.lengthOf(screen.getAllByRole("option"), 2))
    return result
  }

  // "Only owner"/"Moira Lists" labels and the Moira placeholder each appear
  // twice (view group + admin group), so every query below is scoped to the
  // right <section class="permission-group"> via its heading.
  const permSection = heading =>
    screen
      .getByRole("heading", { name: heading })
      .closest("section.permission-group")
  const VIEW = "Who can view videos?"
  const ADMIN = "Who can upload/edit videos?"
  const PERM_LABEL = {
    [PERM_CHOICE_NONE]:  "Only owner",
    [PERM_CHOICE_LISTS]: "Moira Lists"
  }

  // eslint-disable-next-line no-unused-vars
  for (const isNew of [true, false]) {
    describe(`with isNew=${String(isNew)}`, () => {
      const submitText = isNew ? "Create Collection" : "Save"

      beforeEach(() => {
        if (isNew) {
          store.dispatch(showNewCollectionDialog())
        } else {
          store.dispatch(showEditCollectionDialog(collection))
        }
      })

      // eslint-disable-next-line no-unused-vars
      for (const [prop, actionType, newValue, getTarget, interaction] of [
        [
          "title",
          SET_COLLECTION_TITLE,
          "new title",
          () => screen.getByLabelText("Collection Title"),
          "change"
        ],
        [
          "viewChoice",
          SET_VIEW_CHOICE,
          isNew ? PERM_CHOICE_LISTS : PERM_CHOICE_NONE,
          () =>
            within(permSection(VIEW)).getByRole("radio", {
              name: PERM_LABEL[isNew ? PERM_CHOICE_LISTS : PERM_CHOICE_NONE]
            }),
          "click"
        ],
        [
          "viewLists",
          SET_VIEW_LISTS,
          "a,b,c",
          () =>
            within(permSection(VIEW)).getByPlaceholderText(/Add Moira list/),
          "change"
        ],
        [
          "ownerId",
          SET_OWNER_ID,
          2,
          () => screen.getByRole("combobox", { name: "Owner" }),
          "change"
        ],
        [
          "adminChoice",
          SET_ADMIN_CHOICE,
          isNew ? PERM_CHOICE_LISTS : PERM_CHOICE_NONE,
          () =>
            within(permSection(ADMIN)).getByRole("radio", {
              name: PERM_LABEL[isNew ? PERM_CHOICE_LISTS : PERM_CHOICE_NONE]
            }),
          "click"
        ],
        [
          "adminLists",
          SET_ADMIN_LISTS,
          "a,b,c",
          () =>
            within(permSection(ADMIN)).getByPlaceholderText(/Add Moira list/),
          "change"
        ]
      ]) {
        it(`sets ${prop}`, async () => {
          await renderDialog()
          const target = getTarget()
          const state = await listenForActions([actionType], () => {
            if (interaction === "click") {
              fireEvent.click(target)
            } else {
              fireEvent.change(target, { target: { value: String(newValue) } })
            }
          })
          assert.equal(getCollectionForm(state.collectionUi)[prop], newValue)
        })
      }

      /*
       * Description is not in the table above: it is a rich-text editor, not a
       * form field. It holds its document in a contenteditable element and
       * reports serialized HTML through onChange, so there is no value to
       * fireEvent.change. Driving it the way an author does - through a toolbar
       * control - is what exercises the wiring.
       */
      describe("description", () => {
        const editor = () =>
          document.querySelector("#collection-desc .ProseMirror")

        // The editor engine is a split chunk, so it arrives after mount.
        const renderWithEditor = async (props = {}) => {
          const result = await renderDialog(props)
          await waitFor(() => assert.isNotNull(editor()))
          return result
        }

        it("stores what the editor reports, as HTML", async () => {
          await renderWithEditor()
          const state = await listenForActions([SET_COLLECTION_DESC], () => {
            fireEvent.click(
              screen.getByRole("button", { name: "Bulleted list" })
            )
          })
          assert.include(
            getCollectionForm(state.collectionUi).description,
            "<ul>"
          )
        })

        it("shows the stored description as markup", async () => {
          store.dispatch(setCollectionDesc("<p>stored <em>text</em></p>"))
          await renderWithEditor()
          await waitFor(() =>
            assert.include(editor().innerHTML, "<em>text</em>")
          )
        })
      })

      it("stores form submission errors in state", async () => {
        await renderDialog()
        let expectedActionTypes
        const expectedErrorMessage =
          "Failed to parse URL from /api/v0/collections/"
        if (isNew) {
          expectedActionTypes = [
            actions.collectionsList.post.requestType,
            "RECEIVE_POST_COLLECTIONS_LIST_FAILURE",
            SET_COLLECTION_FORM_ERRORS,
            CLEAR_COLLECTION_ERRORS
          ]
        } else {
          expectedActionTypes = [
            actions.collections.patch.requestType,
            "RECEIVE_PATCH_COLLECTIONS_FAILURE",
            SET_COLLECTION_FORM_ERRORS,
            CLEAR_COLLECTION_ERRORS
          ]
        }
        await listenForActions(expectedActionTypes, () => {
          fireEvent.click(screen.getByRole("button", { name: submitText }))
        })

        const actualError = store.getState().collectionUi.errors
        assert.include(actualError.message, expectedErrorMessage)
      })

      it("sends a request to the right endpoint when the form is submitted", async () => {
        const listInput = "list1,list2,list3"
        const expectedListRequestData = ["list1", "list2", "list3"]
        const historyPushStub = sandbox.stub()
        await renderDialog({
          history: {
            push: historyPushStub
          }
        })
        store.dispatch(setAdminChoice(PERM_CHOICE_LISTS))
        store.dispatch(setAdminLists(listInput))
        store.dispatch(setViewChoice(PERM_CHOICE_LISTS))
        store.dispatch(setViewLists(listInput))
        store.dispatch(setCollectionDesc("new description"))
        store.dispatch(setCollectionTitle("new title"))
        store.dispatch(setEdxCourseId("edx-course-id"))
        store.dispatch(setOwnerId(1))

        sandbox.stub(api, "getCollections").returns(Promise.resolve({}))
        let apiStub, expectedActionTypes
        if (isNew) {
          apiStub = sandbox
            .stub(api, "createCollection")
            .returns(Promise.resolve(collection))
          expectedActionTypes = [
            actions.collectionsList.post.requestType,
            actions.collectionsList.post.successType,
            toastActions.constants.ADD_MESSAGE,
            actions.collectionsList.get.requestType,
            CLEAR_COLLECTION_FORM
          ]
        } else {
          apiStub = sandbox
            .stub(api, "updateCollection")
            .returns(Promise.resolve(collection))
          expectedActionTypes = [
            actions.collections.patch.requestType,
            actions.collections.patch.successType,
            toastActions.constants.ADD_MESSAGE,
            actions.collectionsList.get.requestType,
            CLEAR_COLLECTION_FORM
          ]
        }

        await listenForActions(expectedActionTypes, () => {
          fireEvent.click(screen.getByRole("button", { name: submitText }))
        })

        const expectedRequestPayload = {
          title:             "new title",
          description:       "new description",
          view_lists:        expectedListRequestData,
          admin_lists:       expectedListRequestData,
          edx_course_id:     "edx-course-id",
          owner:             1,
          is_logged_in_only: false
        }

        if (isNew) {
          sinon.assert.calledWith(apiStub, expectedRequestPayload)
          sinon.assert.calledWith(
            historyPushStub,
            makeCollectionUrl(collection.key)
          )
        } else {
          sinon.assert.calledWith(
            apiStub,
            collection.key,
            expectedRequestPayload
          )
          sinon.assert.notCalled(historyPushStub)
        }
        assert.isTrue(store.getState().collectionUi.isNew)
      })

      it("does not send edx course id in the API request if isEdxCourseAdmin=false", async () => {
        await renderDialog({
          isEdxCourseAdmin: false,
          history:          {
            push: sandbox.stub()
          }
        })
        // The field itself is conditionally rendered -- the visible half of
        // the same behaviour the payload assertion below pins on the wire.
        assert.isNull(screen.queryByLabelText("edx Course ID"))

        store.dispatch(setAdminChoice(PERM_CHOICE_NONE))
        store.dispatch(setViewChoice(PERM_CHOICE_NONE))
        store.dispatch(setCollectionDesc("new description"))
        store.dispatch(setCollectionTitle("new title"))

        sandbox.stub(api, "getCollections").returns(Promise.resolve({}))
        let apiStub, expectedActionTypes
        if (isNew) {
          apiStub = sandbox
            .stub(api, "createCollection")
            .returns(Promise.resolve(collection))
          expectedActionTypes = [
            actions.collectionsList.post.requestType,
            actions.collectionsList.post.successType
          ]
        } else {
          apiStub = sandbox
            .stub(api, "updateCollection")
            .returns(Promise.resolve(collection))
          expectedActionTypes = [
            actions.collections.patch.requestType,
            actions.collections.patch.successType
          ]
        }

        await listenForActions(expectedActionTypes, () => {
          fireEvent.click(screen.getByRole("button", { name: submitText }))
        })

        const payloadArg = isNew ?
          apiStub.firstCall.args[0] :
          apiStub.firstCall.args[1]
        assert.doesNotHaveAnyKeys(payloadArg, "edx_course_id")
      })

      it("adds toast messages", async () => {
        const historyPushStub = sandbox.stub()
        await renderDialog({
          history: {
            push: historyPushStub
          }
        })
        sandbox.stub(api, "getCollections").returns(Promise.resolve({}))
        let expectedActionTypes
        if (isNew) {
          sandbox
            .stub(api, "createCollection")
            .returns(Promise.resolve(collection))
          expectedActionTypes = [
            actions.collectionsList.post.requestType,
            actions.collectionsList.post.successType,
            toastActions.constants.ADD_MESSAGE
          ]
        } else {
          sandbox
            .stub(api, "updateCollection")
            .returns(Promise.resolve(collection))
          expectedActionTypes = [
            actions.collections.patch.requestType,
            actions.collections.patch.successType,
            toastActions.constants.ADD_MESSAGE
          ]
        }

        const state = await listenForActions(expectedActionTypes, () => {
          fireEvent.click(screen.getByRole("button", { name: submitText }))
        })

        if (isNew) {
          assert.deepEqual(state.toast.messages, [
            {
              key:     "collection-created",
              content: "Collection created",
              icon:    "check"
            }
          ])
        } else {
          assert.deepEqual(state.toast.messages, [
            {
              key:     "collection-updated",
              content: "Changes saved",
              icon:    "check"
            }
          ])
        }
      })

      it("updates collections list for drawer", async () => {
        const historyPushStub = sandbox.stub()
        await renderDialog({
          history: {
            push: historyPushStub
          }
        })
        const getCollectionsStub = sandbox
          .stub(api, "getCollections")
          .returns(Promise.resolve({}))
        if (isNew) {
          sandbox
            .stub(api, "createCollection")
            .returns(Promise.resolve(collection))
        } else {
          sandbox
            .stub(api, "updateCollection")
            .returns(Promise.resolve(collection))
        }

        fireEvent.click(screen.getByRole("button", { name: submitText }))

        // A successful submit re-fetches the collection list so the nav
        // drawer updates (CollectionFormDialog.js's submitForm). Asserting
        // that api.getCollections -- the real boundary behind
        // actions.collectionsList.get() -- was reached is a strictly
        // stronger check than the old `calledWith(dispatch, undefined)`,
        // which passed against an unconfigured stub's return value.
        await waitFor(() => sinon.assert.called(getCollectionsStub))
      })

      it("renders the owner dropdown and can change value", async () => {
        await renderDialog()

        const options = screen.getAllByRole("option")
        assert.equal(options.length, 2, "Should have 2 user options")
        assert.equal(options[0].textContent, "user1 (user1@example.com)")
        assert.equal(options[1].textContent, "user2 (user2@example.com)")

        // Test changing the selected owner
        await listenForActions([SET_OWNER_ID], () => {
          fireEvent.change(screen.getByRole("combobox", { name: "Owner" }), {
            target: {
              value: "2"
            }
          })
        })

        const state = store.getState()
        assert.equal(getCollectionForm(state.collectionUi).ownerId, 2)
      })

      it("sends the owner in the API request when it is set", async () => {
        await renderDialog({
          history: {
            push: sandbox.stub()
          }
        })

        store.dispatch(setAdminChoice(PERM_CHOICE_NONE))
        store.dispatch(setViewChoice(PERM_CHOICE_NONE))
        store.dispatch(setCollectionTitle("new title"))
        store.dispatch(setOwnerId(2)) // Set owner ID to 2

        sandbox.stub(api, "getCollections").returns(Promise.resolve({}))
        let apiStub, expectedActionTypes
        if (isNew) {
          apiStub = sandbox
            .stub(api, "createCollection")
            .returns(Promise.resolve(collection))
          expectedActionTypes = [
            actions.collectionsList.post.requestType,
            actions.collectionsList.post.successType
          ]
        } else {
          apiStub = sandbox
            .stub(api, "updateCollection")
            .returns(Promise.resolve(collection))
          expectedActionTypes = [
            actions.collections.patch.requestType,
            actions.collections.patch.successType
          ]
        }

        await listenForActions(expectedActionTypes, () => {
          fireEvent.click(screen.getByRole("button", { name: submitText }))
        })

        const payloadArg = isNew ?
          apiStub.firstCall.args[0] :
          apiStub.firstCall.args[1]

        assert.equal(
          payloadArg.owner,
          2,
          "Owner ID should be 2 in the API request"
        )
      })

      it("fetches users on component mount", async () => {
        await renderDialog()

        // state.users has exactly one consumer -- the Owner <option> list
        // rendered above by renderDialog's waitFor -- so the two rendered
        // options *are* "fetchPotentialCollectionOwners populated state.users
        // with 2 users". This assertion on the api stub is a stronger
        // boundary than the old `sinon.assert.called(dispatchStub)`: it also
        // pins the collectionKey that was actually sent to the api layer.
        sinon.assert.calledWith(
          getPotentialCollectionOwnersStub,
          "00000000-0000-0000-0000-000000000000"
        )
      })

      it("handles API errors when fetching users", async () => {
        getPotentialCollectionOwnersStub.returns(
          Promise.reject(new Error("Failed to fetch users"))
        )
        // console.error writes to stderr, and scripts/test/js_test.sh's
        // allowlist is frozen -- "Error fetching users:" is not in it, so
        // this stub must exist before the render below.
        const consoleErrorStub = sandbox.stub(console, "error")

        // No <option>s will ever render here (the fetch rejects), so use a
        // bare render -- renderDialog's waitFor would time out.
        await listenForActions(
          [
            actions.potentialCollectionOwners.get.requestType,
            actions.potentialCollectionOwners.get.failureType,
            SET_COLLECTION_FORM_ERRORS,
            CLEAR_COLLECTION_ERRORS
          ],
          () => {
            renderComponent()
          }
        )

        sinon.assert.calledWithMatch(consoleErrorStub, "Error fetching users:")
        assert.equal(
          store.getState().collectionUi.errors.message,
          "Failed to fetch users"
        )
      })

      it("does not fetch users when collectionKey is not provided", () => {
        const consoleLogStub = sandbox.stub(console, "log")

        renderComponent({ collectionKey: undefined })

        sinon.assert.notCalled(getPotentialCollectionOwnersStub)
        assert.lengthOf(screen.queryAllByRole("option"), 0)
        assert.isNotNull(screen.getByRole("combobox", { name: "Owner" }))
        sinon.assert.calledWithMatch(
          consoleLogStub,
          "No collection key provided, skipping potential owner fetch."
        )
      })
    })
  }
})
