// @flow
import React from 'react';
import sinon from 'sinon';
import { mount } from 'enzyme';
import { assert } from 'chai';
import { Provider } from 'react-redux';
import configureTestStore from 'redux-asserts';

import CollectionFormDialog, { makeInitializedForm } from './CollectionFormDialog';

import rootReducer from '../../reducers';
import { actions } from '../../actions';
import {
  setAdminChoice,
  setAdminLists,
  setViewChoice,
  setViewLists,
  setCollectionDesc,
  setCollectionTitle,

  SET_COLLECTION_TITLE,
  SET_COLLECTION_DESC,
  SET_ADMIN_CHOICE,
  SET_ADMIN_LISTS,
  SET_VIEW_CHOICE,
  SET_VIEW_LISTS,
  INIT_COLLECTION_FORM, startNewCollectionDialog,
} from '../../actions/collectionUi';
import {
  getCollectionForm,
  INITIAL_UI_STATE,
} from '../../reducers/collectionUi';
import {
  PERM_CHOICE_LISTS,
  PERM_CHOICE_NONE,
} from '../../lib/dialog';
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


  for (const isNew of [true, false]) {
    describe(`isNew is ${String(isNew)}`, () => {
      beforeEach(() => {
        store.dispatch(startNewCollectionDialog(isNew ? null : collection));
      });

      for (const [selector, prop, actionType, newValue] of [
        ["#collection-title", "title", SET_COLLECTION_TITLE, "new title"],
        ["#collection-desc", "description", SET_COLLECTION_DESC, "new description"],
        ["#view-perms-view-only-me", "viewChoice", SET_VIEW_CHOICE, isNew ? PERM_CHOICE_LISTS : PERM_CHOICE_NONE],
        ["#view-moira-input", "viewLists", SET_VIEW_LISTS, 'a,b,c'],
        ["#admin-perms-admin-only-me", "adminChoice", SET_ADMIN_CHOICE, isNew ? PERM_CHOICE_LISTS : PERM_CHOICE_NONE],
        ["#admin-moira-input", "adminLists", SET_ADMIN_LISTS, 'a,b,c'],
      ]) {
        it(`sets ${prop}`, async () => {
          let wrapper = await renderComponent();
          let state = await listenForActions([actionType], () => {
            wrapper.find(selector).simulate('change', {
              target: {
                value: newValue
              }
            });
          });
          assert.equal(getCollectionForm(state.collectionUi)[prop], newValue);
        });
      }

      it('sends a request to the right endpoint when the form is submitted', async () => {
        let listInput = "list1,list2,list3";
        let expectedListRequestData = ["list1", "list2", "list3"];
        let wrapper = await renderComponent();
        store.dispatch(setAdminChoice(PERM_CHOICE_LISTS));
        store.dispatch(setAdminLists(listInput));
        store.dispatch(setViewChoice(PERM_CHOICE_LISTS));
        store.dispatch(setViewLists(listInput));
        store.dispatch(setCollectionDesc("new description"));
        store.dispatch(setCollectionTitle("new title"));

        let apiStub, expectedActionTypes;
        if (isNew) {
          apiStub = sandbox.stub(api, 'createCollection').returns(Promise.resolve(collection));
          expectedActionTypes = [
            actions.collectionsList.post.requestType,
            actions.collectionsList.post.successType,
            INIT_COLLECTION_FORM,
          ];
        } else {
          apiStub = sandbox.stub(api, 'updateCollection').returns(Promise.resolve(collection));
          expectedActionTypes = [
            actions.collections.patch.requestType,
            actions.collections.patch.successType,
            INIT_COLLECTION_FORM,
          ];
        }

        await listenForActions(expectedActionTypes, () => {
          // Calling click handler directly due to MDC limitations (can't use enzyme's 'simulate')
          wrapper.find('Dialog').prop('onAccept')();
        });

        const expectedRequestPayload = {
          title: "new title",
          description: "new description",
          view_lists: expectedListRequestData,
          admin_lists: expectedListRequestData
        };

        if (isNew) {
          sinon.assert.calledWith(apiStub, expectedRequestPayload);
        } else {
          sinon.assert.calledWith(apiStub, collection.key, expectedRequestPayload);
        }
        sinon.assert.calledWith(hideDialogStub);

        let expectedForm = isNew ? makeInitializedForm() : makeInitializedForm(collection);

        // hasn't changed, and form is reverted to initial state
        assert.equal(store.getState().collectionUi.isNew, isNew);
        assert.deepEqual(getCollectionForm(store.getState().collectionUi), expectedForm);
      });
    });
  }

  it('makes a new form without a collection', () => {
    assert.deepEqual(makeInitializedForm(), {
      key: '',
      title: '',
      description: '',
      adminChoice: PERM_CHOICE_NONE,
      adminLists: "",
      viewChoice: PERM_CHOICE_NONE,
      viewLists: "",
    });
  });

  it('makes a new form with an existing collection', () => {
    assert.deepEqual(makeInitializedForm(collection), {
      key: collection.key,
      title: collection.title,
      description: collection.description,
      adminChoice: PERM_CHOICE_LISTS,
      adminLists: collection.admin_lists.join(","),
      viewChoice: PERM_CHOICE_LISTS,
      viewLists: collection.view_lists.join(","),
    });
  });
});
