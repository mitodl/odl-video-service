// @flow
/* global SETTINGS: false */
import React from 'react';
import { assert } from 'chai';
import { mount } from 'enzyme';
import sinon from 'sinon';
import configureTestStore from 'redux-asserts';
import { Provider } from 'react-redux';
import rootReducer from '../../reducers';
import * as api from '../../lib/api';
import { actions } from '../../actions';
import Drawer from './Drawer';
import { makeCollection } from '../../factories/collection';
import { makeCollectionUrl } from "../../lib/urls";
import type { Collection } from "../../flow/collectionTypes";
import { SHOW_DIALOG } from "../../actions/commonUi";
import { SET_IS_NEW } from "../../actions/collectionUi";
import { DIALOGS } from "../../constants";

describe("Drawer", () => {
  let sandbox, store, collections: Array<Collection>, listenForActions, getCollectionsStub;
  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    store = configureTestStore(rootReducer);
    SETTINGS.user = 'foo@mit.edu';
    collections = [makeCollection(), makeCollection()];
    listenForActions = store.createListenForActions();
    getCollectionsStub = sandbox.stub(api, 'getCollections').returns(Promise.resolve(collections));
  });

  afterEach(() => {
    sandbox.restore();
  });

  const renderDrawer = async (props = {}) => {
    let wrapper;
    await listenForActions([
      actions.collectionsList.get.requestType,
      actions.collectionsList.get.successType,
    ], () => {
      wrapper = mount(
        <Provider store={store}>
          <Drawer
            {...props}
          />
        </Provider>
      );
    });
    if (!wrapper) {
      throw "Never will happen, make flow happy";
    }
    return wrapper;
  };

  it('drawer element is rendered with the correct user', async () => {
    let wrapper = await renderDrawer();
    let drawerNode = wrapper.find('.mdc-list-item .mdc-link').at(0);
    assert.isTrue(drawerNode.text().startsWith('foo@mit.edu'));
  });

  it('drawer element is rendered with collections', async () => {
    let wrapper = await renderDrawer();
    let drawerNode = wrapper.find('.mdc-list-item .mdc-link').at(1);
    assert.equal(drawerNode.props().href, '/logout/');
    assert.isTrue(drawerNode.text().endsWith('Log out'));
  });

  it('drawer element is rendered with collections list', async () => {
    let wrapper = await renderDrawer();
    [0,1].forEach(function(col) {
      let drawerNode = wrapper.find('.mdc-list-item .mdc-temporary-drawer--selected').at(col);
      assert.equal(drawerNode.text(), collections[col].title);
      assert.equal(drawerNode.props().href, makeCollectionUrl(collections[col].key));
    });
  });

  it('drawer element is rendered with a logout link', async () => {
    let wrapper = await renderDrawer();
    let drawerNode = wrapper.find('.mdc-list-item .mdc-link').at(1);
    assert.equal(drawerNode.props().href, '/logout/');
    assert.isTrue(drawerNode.text().endsWith('Log out'));
  });

  it('fetches requirements on load', async () => {
    await renderDrawer();
    sinon.assert.calledWith(getCollectionsStub);
  });

  it('closes the drawer if the user is clicked', async () => {
    let onDrawerCloseStub = sandbox.stub();
    let wrapper = await renderDrawer({
      onDrawerClose: onDrawerCloseStub
    });
    wrapper.find("#collapse_item").get(0).click();
    sinon.assert.calledWith(onDrawerCloseStub);
  });

  it('hides the create collection button if SETTINGS.editable is false', async () => {
    SETTINGS.editable = false;
    let wrapper = await renderDrawer();
    assert.lengthOf(wrapper.find(".create-collection-button"), 0);
  });

  it('opens the collection dialog when the create collection button is clicked', async () => {
    SETTINGS.editable = true;
    let onDrawerCloseStub = sandbox.stub();
    let wrapper = await renderDrawer({
      onDrawerClose: onDrawerCloseStub
    });
    let state = await listenForActions([
      SHOW_DIALOG,
      SET_IS_NEW,
    ], () => {
      wrapper.find(".create-collection-button").get(0).click();
    });

    assert.isFalse(state.commonUi.drawerOpen);
    assert.isTrue(state.commonUi.dialogVisibility[DIALOGS.COLLECTION_FORM]);
    sinon.assert.calledWith(onDrawerCloseStub);
  });
});
