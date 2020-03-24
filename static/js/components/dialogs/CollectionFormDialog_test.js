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
  SET_COLLECTION_TITLE,
  SET_COLLECTION_DESC,
  SET_ADMIN_CHOICE,
  SET_ADMIN_LISTS,
  SET_VIEW_CHOICE,
  SET_VIEW_LISTS,
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
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    hideDialogStub = sandbox.stub()
    collection = makeCollection()
    uiState = INITIAL_UI_STATE
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
            {...props}
          />
        </div>
      </Provider>
    )
  }

  for (const isNew of [true, false]) {
    describe(`with isNew=${String(isNew)}`, () => {
      beforeEach(() => {
        if (isNew) {
          store.dispatch(showNewCollectionDialog())
        } else {
          store.dispatch(showEditCollectionDialog(collection))
        }
      })

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
        const expectedError = "Error: only absolute urls are supported"
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

        assert.equal(store.getState().collectionUi.errors, expectedError)
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
          title:         "new title",
          description:   "new description",
          view_lists:    expectedListRequestData,
          admin_lists:   expectedListRequestData,
          edx_course_id: "edx-course-id"
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

        const payloadArg = isNew
          ? apiStub.firstCall.args[0]
          : apiStub.firstCall.args[1]
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
    })
  }
})
