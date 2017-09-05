// @flow
import { assert } from 'chai';

import { getActiveCollectionDetail } from './collection';
import { makeCollection } from '../factories/collection';

import type { Collection } from "../flow/collectionTypes";
import type { RestState } from "../flow/restTypes";

describe('collection library function', () => {
  describe('getActiveCollectionDetail ', () => {
    let collection = makeCollection();
    let collectionsState: RestState<Collection>;

    beforeEach(() => {
      collectionsState = {
        data: collection,
        processing: false,
        loaded:     false
      };
    });

    it('returns the active collection when data exists', () => {
      collectionsState.loaded = true;
      assert.deepEqual(getActiveCollectionDetail({collections: collectionsState}), collection);
    });

    it('returns null when the collection is still loading', () => {
      collectionsState.loaded = false;
      assert.isNull(getActiveCollectionDetail({collections: collectionsState}));
    });

    [
      [{collections: null}, "null collections object"],
      [{}, "no collections object"]
    ].forEach(([state, testDescriptor]) => {
      it(`returns null when the state has ${testDescriptor}`, () => {
        assert.isNull(getActiveCollectionDetail(state));
      });
    });
  });
});
