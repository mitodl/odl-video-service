import { assert } from "chai"

import {
  getActiveCollectionDetail,
  getCollectionForm,
  getFormKey,
  makeInitializedForm
} from "./collection"
import { makeCollection } from "../factories/collection"
import { INITIAL_UI_STATE } from "../reducers/collectionUi"
import { PERM_CHOICE_NONE, PERM_CHOICE_LISTS } from "./dialog"

import type { Collection, CollectionFormState } from "../types/collectionTypes"
import type { RestState } from "../types/restTypes"
import { DESCRIPTION_FORMAT_TEXT } from "../constants"

// getActiveCollectionDetail's parameter type, named here so the table of
// degenerate states below can be annotated with it.
type CollectionDetailState = {
  collections?: RestState<Collection> | null
}

describe("collection library function", () => {
  describe("getActiveCollectionDetail ", () => {
    const collection = makeCollection()
    let collectionsState: RestState<Collection>

    beforeEach(() => {
      collectionsState = {
        data:       collection,
        processing: false,
        loaded:     false
      }
    })

    it("returns the active collection when data exists", () => {
      collectionsState.loaded = true
      assert.deepEqual(
        getActiveCollectionDetail({ collections: collectionsState }),
        collection
      )
    })

    it("returns null when the collection is still loading", () => {
      collectionsState.loaded = false
      assert.isNull(
        getActiveCollectionDetail({ collections: collectionsState })
      )
    })
    ;(
      [
        [{ collections: null }, "null collections object"],
        [{}, "no collections object"]
      ] as Array<[CollectionDetailState, string]>
    ).forEach(([state, testDescriptor]) => {
      it(`returns null when the state has ${testDescriptor}`, () => {
        assert.isNull(getActiveCollectionDetail(state))
      })
    })
  })

  // eslint-disable-next-line no-unused-vars
  for (const isNew of [true, false]) {
    describe(`with isNew = ${String(isNew)}`, () => {
      it("getFormKey returns the key for the form", () => {
        assert.equal(
          getFormKey(isNew),
          isNew ? "newCollectionForm" : "editCollectionForm"
        )
      })

      it("getCollectionForm gets the expected form", () => {
        // `isNew` has to be set on the state, since that is what
        // getCollectionForm reads. Passing INITIAL_UI_STATE unchanged left it
        // true for both halves of this loop, and the isNew=false case only
        // held because the two forms started as the same object.
        const collectionUi = { ...INITIAL_UI_STATE, isNew }
        const key = isNew ? "newCollectionForm" : "editCollectionForm"
        // this is explicitly comparing identity, not value equality
        assert.isTrue(getCollectionForm(collectionUi) === collectionUi[key])
      })
    })
  }

  it("makes a new form without a collection", () => {
    // lib/collection declares the parameter as required even though the
    // function synthesises a blank collection when it is absent -- the path
    // this test covers. Casting the reference keeps the call site the
    // zero-argument call the implementation supports.
    const makeBlankForm = makeInitializedForm as () => CollectionFormState
    assert.deepEqual(makeBlankForm(), {
      key:                "",
      title:              "",
      description:        "",
      description_format: DESCRIPTION_FORMAT_TEXT,
      adminChoice:        PERM_CHOICE_NONE,
      adminLists:         "",
      viewChoice:         PERM_CHOICE_NONE,
      viewLists:          "",
      edxCourseId:        "",
      videoCount:         0,
      ownerId:            null,
      ownerInfo:          {
        id:       null,
        username: "",
        email:    ""
      }
    })
  })

  it("makes a new form with an existing collection", () => {
    const collection = makeCollection()
    assert.deepEqual(makeInitializedForm(collection), {
      key:                collection.key,
      title:              collection.title,
      description:        collection.description,
      description_format: collection.description_format,
      adminChoice:        PERM_CHOICE_LISTS,
      adminLists:         collection.admin_lists.join(","),
      viewChoice:         PERM_CHOICE_LISTS,
      viewLists:          collection.view_lists.join(","),
      edxCourseId:        collection.edx_course_id,
      videoCount:         collection.video_count,
      ownerId:            collection.owner || null,
      ownerInfo:          collection.owner_info || {
        id:       null,
        username: "",
        email:    ""
      }
    })
  })
})
