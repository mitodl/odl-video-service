// @flow
import React from 'react';
import sinon from 'sinon';
import { mount } from 'enzyme';
import { assert } from 'chai';
import { Provider } from 'react-redux';
import configureTestStore from 'redux-asserts';

import CollectionFormDialog from './CollectionFormDialog';

import rootReducer from '../../reducers';
import { actions } from '../../actions';
import {
  INIT_COLLECTION_FORM,
  setAdminChoice,
  setAdminLists,
  setViewChoice,
  setViewLists
} from '../../actions/collectionUi';
import { INITIAL_UI_STATE } from '../../reducers/collectionUi';
import { PERM_CHOICE_LISTS } from '../../lib/dialog';
import * as api from '../../lib/api';
import { makeCollection } from "../../factories/collection";

describe('CollectionFormDialog', () => {
  let sandbox, store, listenForActions, hideDialogStub, collection, uiState;

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    store = configureTestStore(rootReducer);
    listenForActions = store.createListenForActions();
    hideDialogStub = sandbox.stub();
    collection = makeCollection();
    uiState = INITIAL_UI_STATE;
  });

  afterEach(() => {
    sandbox.restore();
  });

  const renderComponent = (props = {}) => {
    return mount(
      <Provider store={store}>
        <div>
          <CollectionFormDialog
            collectionUi={uiState}
            collection={collection}
            open={true}
            hideDialog={hideDialogStub}
            { ...props }
          />
        </div>
      </Provider>
    );
  };

  it('initializes the form when a collection object exists and does not match the form collection key', async () => {
    let wrapper;
    await listenForActions([INIT_COLLECTION_FORM], () => {
      wrapper = renderComponent();
    }).then(() => {
      assert.notDeepEqual(
        wrapper.find('CollectionFormDialog').prop('collectionUi').collectionForm,
        uiState.collectionForm
      );
    });
  });

  it('does not initialize the form when the collection object matches the form collection key', () => {
    uiState.collectionForm.key = collection.key;
    let wrapper = renderComponent();
    assert.deepEqual(
      wrapper.find('CollectionFormDialog').prop('collectionUi').collectionForm,
      uiState.collectionForm
    );
  });

  it('sends a patch request to the collection detail endpoint when the form is submitted', async () => {
    let listInput = "list1,list2,list3";
    let expectedListRequestData = ["list1", "list2", "list3"];
    let wrapper = await renderComponent();
    store.dispatch(setAdminChoice(PERM_CHOICE_LISTS));
    store.dispatch(setAdminLists(listInput));
    store.dispatch(setViewChoice(PERM_CHOICE_LISTS));
    store.dispatch(setViewLists(listInput));

    let updateCollectionStub = sandbox.stub(api, 'updateCollection').returns(Promise.resolve(collection));
    await listenForActions([
      actions.collections.patch.requestType,
      actions.collections.patch.successType
    ], () => {
      // Calling click handler directly due to MDC limitations (can't use enzyme's 'simulate')
      wrapper.find('Dialog').prop('onAccept')();
    });

    sinon.assert.calledWith(updateCollectionStub, collection.key);
    let payload = updateCollectionStub.getCall(0).args[1];
    assert.deepEqual(
      payload,
      {
        title: collection.title,
        description: collection.description,
        view_lists: expectedListRequestData,
        admin_lists: expectedListRequestData
      }
    );
  });
});