// @flow
import configureTestStore from 'redux-asserts';
import { assert } from 'chai';
import sinon from 'sinon';

import rootReducer from '../reducers';
import { actions } from '../actions';
import { makeCollection } from "../factories/collection";
import * as api from '../lib/api';

describe('collections endpoints', () => {
  let store, dispatchThen, collections, sandbox;

  beforeEach(() => {
    store = configureTestStore(rootReducer);
    sandbox = sinon.sandbox.create();
    dispatchThen = store.createDispatchThen();

    collections = [makeCollection(), makeCollection()];
  });

  afterEach(() => {
    sandbox.restore();
  });

  it('adds a new collection to the beginning of the list', async () => {
    sandbox.stub(api, 'getCollections').returns(Promise.resolve(collections));
    let state = await dispatchThen(
      actions.collectionsList.get(),
      [
        actions.collectionsList.get.requestType,
        actions.collectionsList.get.successType,
      ]
    );

    assert.deepEqual(state.collectionsList.data, collections);

    let newCollection = makeCollection();
    sandbox.stub(api, 'createCollection').returns(Promise.resolve(newCollection));
    state = await dispatchThen(
      actions.collectionsList.post(newCollection),
      [
        actions.collectionsList.post.requestType,
        actions.collectionsList.post.successType,
      ]
    );
    assert.deepEqual(state.collectionsList.data, [newCollection, ...collections]);
  });
});
