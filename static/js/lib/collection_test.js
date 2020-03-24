// @flow
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

import type { Collection } from "../flow/collectionTypes"
import type { RestState } from "../flow/restTypes"

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
    ;[
      [{ collections: null }, "null collections object"],
      [{}, "no collections object"]
    ].forEach(([state, testDescriptor]) => {
      it(`returns null when the state has ${testDescriptor}`, () => {
        assert.isNull(getActiveCollectionDetail(state))
      })
    })
  })

  for (const isNew of [true, false]) {
    describe(`with isNew = ${String(isNew)}`, () => {
      it("getFormKey returns the key for the form", () => {
        assert.equal(
          getFormKey(isNew),
          isNew ? "newCollectionForm" : "editCollectionForm"
        )
      })

      it("getCollectionForm gets the expected form", () => {
        const collectionUi = INITIAL_UI_STATE
        const key = isNew ? "newCollectionForm" : "editCollectionForm"
        // this is explicitly comparing identity, not value equality
        assert.isTrue(getCollectionForm(collectionUi) === collectionUi[key])
      })
    })
  }

  it("makes a new form without a collection", () => {
    assert.deepEqual(makeInitializedForm(), {
      key:         "",
      title:       "",
      description: "",
      adminChoice: PERM_CHOICE_NONE,
      adminLists:  "",
      viewChoice:  PERM_CHOICE_NONE,
      viewLists:   "",
      edxCourseId: "",
      videoCount:  0
    })
  })

  it("makes a new form with an existing collection", () => {
    const collection = makeCollection()
    assert.deepEqual(makeInitializedForm(collection), {
      key:         collection.key,
      title:       collection.title,
      description: collection.description,
      adminChoice: PERM_CHOICE_LISTS,
      adminLists:  collection.admin_lists.join(","),
      viewChoice:  PERM_CHOICE_LISTS,
      viewLists:   collection.view_lists.join(","),
      edxCourseId: collection.edx_course_id,
      videoCount:  collection.video_count
    })
  })
})
