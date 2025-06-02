// @flow
import { assert } from "chai"
import configureTestStore from "redux-asserts"

import {
  initCollectionForm,
  setSelectedVideoKey,
  setAdminChoice,
  setAdminLists,
  setCollectionDesc,
  setCollectionTitle,
  setViewChoice,
  setViewLists,
  setIsNew,
  clearCollectionForm,
  setOwnerId
} from "../actions/collectionUi"
import rootReducer from "../reducers"
import { INITIAL_COLLECTION_FORM_STATE } from "../reducers/collectionUi"
import { PERM_CHOICE_NONE } from "../lib/dialog"
import { getCollectionForm } from "../lib/collection"
import { createAssertReducerResultState } from "../util/test_utils"
import { INITIAL_UI_STATE } from "./collectionUi"

describe("collectionUi", () => {
  let assertReducerResultState, store

  beforeEach(() => {
    store = configureTestStore(rootReducer)
    assertReducerResultState = createAssertReducerResultState(
      store,
      state => state.collectionUi
    )
  })

  it("has some initial state", () => {
    assert.deepEqual(store.getState().collectionUi, {
      editCollectionForm: INITIAL_COLLECTION_FORM_STATE,
      newCollectionForm:  INITIAL_COLLECTION_FORM_STATE,
      selectedVideoKey:   null,
      isNew:              true
    })
  })

  it("sets the selected video key for the form", () => {
    assertReducerResultState(
      setSelectedVideoKey,
      ui => ui.selectedVideoKey,
      null
    )
  })

  it("sets isNew", () => {
    assertReducerResultState(setIsNew, ui => ui.isNew, true)
  })

  it("resets the dialog to its initial state", () => {
    store.dispatch(setSelectedVideoKey("key"))
    store.dispatch(setIsNew(false))
    store.dispatch(
      initCollectionForm({
        field: "that doesn't belong here"
      })
    )

    store.dispatch(clearCollectionForm())
    assert.deepEqual(store.getState().collectionUi, INITIAL_UI_STATE)
  })

  // eslint-disable-next-line no-unused-vars
  for (const isNew of [true, false]) {
    describe(`when isNew is ${String(isNew)}`, () => {
      beforeEach(() => {
        store.dispatch(setIsNew(isNew))
      })

      it("initializes the collection form", () => {
        store.dispatch(
          initCollectionForm({
            title: "different title"
          })
        )
        assert.deepEqual(getCollectionForm(store.getState().collectionUi), {
          ...INITIAL_COLLECTION_FORM_STATE,
          title: "different title"
        })
      })

      it("sets the collection title", () => {
        assertReducerResultState(
          setCollectionTitle,
          ui => getCollectionForm(ui).title,
          ""
        )
      })

      it("sets the collection description", () => {
        assertReducerResultState(
          setCollectionDesc,
          ui => getCollectionForm(ui).description,
          ""
        )
      })

      it("sets the admin choice", () => {
        assertReducerResultState(
          setAdminChoice,
          ui => getCollectionForm(ui).adminChoice,
          PERM_CHOICE_NONE
        )
      })

      it("sets the admin list", () => {
        assertReducerResultState(
          setAdminLists,
          ui => getCollectionForm(ui).adminLists,
          null
        )
      })

      it("sets the view choice", () => {
        assertReducerResultState(
          setViewChoice,
          ui => getCollectionForm(ui).viewChoice,
          PERM_CHOICE_NONE
        )
      })

      it("sets the view list", () => {
        assertReducerResultState(
          setViewLists,
          ui => getCollectionForm(ui).viewLists,
          null
        )
      })

      it("sets the owner id for the collection", () => {
        const ownerId = 123
        store.dispatch(setOwnerId(ownerId))
        assert.equal(
          getCollectionForm(store.getState().collectionUi).ownerId,
          ownerId
        )
      })
    })
  }
})
