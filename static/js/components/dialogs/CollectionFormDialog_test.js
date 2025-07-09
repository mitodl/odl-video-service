// @flow
import React from "react"
import sinon from "sinon"
import { mount, shallow } from "enzyme"
import { assert } from "chai"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"

import CollectionFormDialog from "./CollectionFormDialog"
import { CollectionFormDialog as UnconnectedCollectionFormDialog } from "./CollectionFormDialog"

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

describe("CollectionFormDialog", () => {
  let sandbox, store, listenForActions, hideDialogStub, collection, uiState

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    hideDialogStub = sandbox.stub()
    collection = makeCollection()
    uiState = INITIAL_UI_STATE

    // Mock the users API response
    sandbox.stub(api, "getPotentialCollectionOwners").returns(Promise.resolve({
      users: [
        { id: 1, username: "user1", email: "user1@example.com" },
        { id: 2, username: "user2", email: "user2@example.com" }
      ]
    }))
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (props = {}) => {
    return mount(
      <Provider store={store}>
        <div>
          <CollectionFormDialog
            collectionUi={uiState}
            collection={collection}
            open={true}
            hideDialog={hideDialogStub}
            isEdxCourseAdmin={true}
            collectionKey={'00000000-0000-0000-0000-000000000000'}
            {...props}
          />
        </div>
      </Provider>
    )
  }

  // eslint-disable-next-line no-unused-vars
  for (const isNew of [true, false]) {
    describe(`with isNew=${String(isNew)}`, () => {
      beforeEach(() => {
        if (isNew) {
          store.dispatch(showNewCollectionDialog())
        } else {
          store.dispatch(showEditCollectionDialog(collection))
        }
      })

      // eslint-disable-next-line no-unused-vars
      for (const [selector, prop, actionType, newValue] of [
        ["#collection-title", "title", SET_COLLECTION_TITLE, "new title"],
        [
          "#collection-desc",
          "description",
          SET_COLLECTION_DESC,
          "new description"
        ],
        [
          "#view-perms-view-only-me",
          "viewChoice",
          SET_VIEW_CHOICE,
          isNew ? PERM_CHOICE_LISTS : PERM_CHOICE_NONE
        ],
        ["#view-moira-input", "viewLists", SET_VIEW_LISTS, "a,b,c"],
        ["#collection-owner", "ownerId", SET_OWNER_ID, 2],
        [
          "#admin-perms-admin-only-me",
          "adminChoice",
          SET_ADMIN_CHOICE,
          isNew ? PERM_CHOICE_LISTS : PERM_CHOICE_NONE
        ],
        ["#admin-moira-input", "adminLists", SET_ADMIN_LISTS, "a,b,c"]
      ]) {
        it(`sets ${prop}`, async () => {
          const wrapper = await renderComponent()
          const state = await listenForActions([actionType], () => {
            wrapper
              .find(selector)
              .hostNodes()
              .simulate("change", {
                target: {
                  value: newValue
                }
              })
          })
          assert.equal(getCollectionForm(state.collectionUi)[prop], newValue)
        })
      }

      it("stores form submission errors in state", async () => {
        const wrapper = await renderComponent()
        let expectedActionTypes
        const expectedErrorMessage = "Failed to parse URL from /api/v0/collections/"
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
          // Calling click handler directly due to MDC limitations (can't use enzyme's 'simulate')
          wrapper.find("Dialog").prop("onAccept")()
        })

        const actualError = store.getState().collectionUi.errors
        assert.include(actualError.message, expectedErrorMessage)
      })

      it("sends a request to the right endpoint when the form is submitted", async () => {
        const listInput = "list1,list2,list3"
        const expectedListRequestData = ["list1", "list2", "list3"]
        const historyPushStub = sandbox.stub()
        const wrapper = await renderComponent({
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
          // Calling click handler directly due to MDC limitations (can't use enzyme's 'simulate')
          wrapper.find("Dialog").prop("onAccept")()
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
        const wrapper = await renderComponent({
          isEdxCourseAdmin: false,
          history:          {
            push: sandbox.stub()
          }
        })

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
          // Calling click handler directly due to MDC limitations (can't use enzyme's 'simulate')
          wrapper.find("Dialog").prop("onAccept")()
        })

        const payloadArg = isNew ?
          apiStub.firstCall.args[0] :
          apiStub.firstCall.args[1]
        assert.doesNotHaveAnyKeys(payloadArg, "edx_course_id")
      })

      it("adds toast messages", async () => {
        const historyPushStub = sandbox.stub()
        const wrapper = await renderComponent({
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
          // Calling click handler directly due to MDC limitations (can't use enzyme's 'simulate')
          wrapper.find("Dialog").prop("onAccept")()
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
        const stubs = {
          // Stub dispatch to return collection, per isNew=true condition.
          dispatch: sandbox.stub().returns(Promise.resolve(collection)),
          history:  {
            push: sandbox.stub()
          },
          collectionsListGet:  sandbox.stub(actions.collectionsList, "get"),
          collectionsListPost: sandbox
            .stub(actions.collectionsList, "post")
            .returns(Promise.resolve(collection)),
          collectionsPatch: sandbox
            .stub(actions.collections, "patch")
            .returns(Promise.resolve())
        }
        const wrapper = shallow(
          <UnconnectedCollectionFormDialog
            dispatch={stubs.dispatch}
            history={stubs.history}
            collectionUi={{ isNew }}
            collectionForm={{}}
          />
        )
        await wrapper.instance().submitForm()
        sinon.assert.calledWith(
          stubs.dispatch,
          stubs.collectionsListGet.returnValues[0]
        )
      })

      it("renders the owner dropdown and can change value", async () => {
        const wrapper = renderComponent()
        // Wait for component to fetch users
        await new Promise(resolve => setTimeout(resolve, 10))
        wrapper.update()

        const select = wrapper.find("#collection-owner").hostNodes()
        assert.ok(select.exists(), "Owner dropdown should be rendered")

        // Check options are rendered correctly
        const options = select.find("option")
        assert.equal(options.length, 2, "Should have 2 user options")
        assert.equal(options.at(0).text(), "user1 (user1@example.com)")
        assert.equal(options.at(1).text(), "user2 (user2@example.com)")

        // Test changing the selected owner
        await listenForActions([SET_OWNER_ID], () => {
          select.simulate("change", {
            target: {
              value: "2"
            }
          })
        })

        const state = store.getState()
        assert.equal(getCollectionForm(state.collectionUi).ownerId, 2)
      })

      it("sends the owner in the API request when it is set", async () => {
        const wrapper = await renderComponent({
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
          wrapper.find("Dialog").prop("onAccept")()
        })

        const payloadArg = isNew ?
          apiStub.firstCall.args[0] :
          apiStub.firstCall.args[1]

        assert.equal(payloadArg.owner, 2, "Owner ID should be 2 in the API request")
      })

      it("fetches users on component mount", async () => {
        // We need to restore the default stub to avoid conflicts
        sandbox.restore()

        // Create a new getPotentialCollectionOwnersStub
        sandbox.stub(api, "getPotentialCollectionOwners").returns(Promise.resolve({
          users: [
            { id: 1, username: "user1", email: "user1@example.com" },
            { id: 2, username: "user2", email: "user2@example.com" }
          ]
        }))

        // Create a dispatch stub that returns the expected data
        const dispatchStub = sandbox.stub()
        dispatchStub.returns(Promise.resolve({
          users: [
            { id: 1, username: "user1", email: "user1@example.com" },
            { id: 2, username: "user2", email: "user2@example.com" }
          ]
        }))

        const wrapper = shallow(
          <UnconnectedCollectionFormDialog
            dispatch={dispatchStub}
            history={{ push: sandbox.stub() }}
            collectionUi={{ isNew: true }}
            collectionForm={{}}
            collectionKey={'00000000-0000-0000-0000-000000000000'}
          />
        )

        // Wait for componentDidMount to finish
        await new Promise(resolve => setTimeout(resolve, 10))

        sinon.assert.called(dispatchStub)
        assert.equal(wrapper.state().users.length, 2)

        // Reinitialize the sandbox with the global stubs for other tests
        sandbox.restore()
        sandbox = sinon.createSandbox()
        sandbox.stub(api, "getPotentialCollectionOwners").returns(Promise.resolve({
          users: [
            { id: 1, username: "user1", email: "user1@example.com" },
            { id: 2, username: "user2", email: "user2@example.com" }
          ]
        }))
      })

      it("handles API errors when fetching users", async () => {
        // Restore the original stub and create a new one that rejects
        sandbox.restore()

        // Create a dispatch stub that rejects the promise
        const dispatchStub = sandbox.stub()
        dispatchStub.returns(Promise.reject(new Error("Failed to fetch users")))

        // Create a stub for console.error
        const consoleErrorStub = sandbox.stub(console, "error")

        const wrapper = shallow(
          <UnconnectedCollectionFormDialog
            dispatch={dispatchStub}
            history={{ push: sandbox.stub() }}
            collectionUi={{ isNew: true }}
            collectionForm={{}}
            collectionKey={'00000000-0000-0000-0000-000000000000'}
          />
        )

        // Create a stub for handleError
        const handleErrorStub = sandbox.stub()
        wrapper.instance().handleError = handleErrorStub

        // Call fetchPotentialCollectionOwners manually
        await wrapper.instance().fetchPotentialCollectionOwners()

        // Verify console.error was called
        sinon.assert.called(consoleErrorStub)

        // Verify handleError was called
        sinon.assert.called(handleErrorStub)
      })

      it("does not fetch users when collectionKey is not provided", async () => {
        sandbox.restore()

        const dispatchStub = sandbox.stub()

        const consoleLogStub = sandbox.stub(console, "log")

        const wrapper = shallow(
          <UnconnectedCollectionFormDialog
            dispatch={dispatchStub}
            history={{ push: sandbox.stub() }}
            collectionUi={{ isNew: true }}
            collectionForm={{}}
          />
        )
        await new Promise(resolve => setTimeout(resolve, 10))

        sinon.assert.notCalled(dispatchStub)
        assert.equal(wrapper.state().users.length, 0)
        sinon.assert.calledWithMatch(consoleLogStub, "No collection key provided, skipping potential owner fetch.")
      })
    })
  }
})
