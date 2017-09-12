// @flow
import React from 'react';
import sinon from 'sinon';
import { mount } from 'enzyme';
import { assert } from 'chai';
import { Provider } from 'react-redux';
import configureTestStore from 'redux-asserts';

import CollectionDetailPage from './CollectionDetailPage';

import * as api from '../lib/api';
import { actions } from '../actions';
import rootReducer from '../reducers';
import { makeCollection } from "../factories/collection";
import { makeVideos } from "../factories/video";
import { expect } from "../util/test_utils";

describe('CollectionDetailPage', () => {
  let sandbox, store, getCollectionStub, collection, listenForActions;
  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    store = configureTestStore(rootReducer);
    listenForActions = store.createListenForActions();
    collection = makeCollection();

    getCollectionStub = sandbox.stub(api, 'getCollection').returns(Promise.resolve(collection));
  });

  afterEach(() => {
    sandbox.restore();
  });

  const renderPage = async (props = {}) => {
    let wrapper;
    // Simulate the react-router match object
    let matchObj = { params: { collectionKey: collection.key } };
    await listenForActions([
      actions.collections.get.requestType,
      actions.collections.get.successType,
    ], () => {
      wrapper = mount(
        <Provider store={store}>
          <CollectionDetailPage
            match={matchObj}
            {...props}
          />
        </Provider>
      );
    });
    if (!wrapper) throw "Never will happen, make flow happy";
    return wrapper;
  };

  it('fetches requirements on load', async () => {
    await renderPage();
    sinon.assert.calledWith(getCollectionStub, collection.key);
  });

  it('renders each video in the collection', async () => {
    let addedVideos = makeVideos(3, collection.key);
    let expectedVideoCount = collection.videos.length + addedVideos.length;
    collection.videos = collection.videos.concat(addedVideos);

    let wrapper = await renderPage();
    assert.lengthOf(wrapper.find("VideoCard"), expectedVideoCount);
  });

  [
    ["Collection description", true, "non-empty description"],
    [null, false, "empty description"]
  ].forEach(([collectionDescription, shouldShow, testDescriptor]) => {
    it(`description ${expect(shouldShow)} be shown with ${testDescriptor}`, async () => {
      collection.description = collectionDescription;
      let wrapper = await renderPage();
      let descriptionEl = wrapper.find("p.description");
      assert.equal(descriptionEl.exists(), shouldShow);
      if (shouldShow) {
        assert.equal(descriptionEl.text(), collectionDescription);
      }
    });
  });

  [
    [2, true, "one or more videos"],
    [0, false, "no videos"]
  ].forEach(([videoCount, shouldShow, testDescriptor]) => {
    it(`video count ${expect(shouldShow)} be shown with ${testDescriptor}`, async () => {
      collection.videos = makeVideos(videoCount, collection.key);
      let wrapper = await renderPage();
      let titleText = wrapper.find(".collection-detail-content h2").text();
      assert.equal(titleText.indexOf(`(${videoCount})`) >= 0, shouldShow);
    });
  });

  it('has a toolbar whose handler will dispatch an action to open the drawer', async () => {
    let wrapper = await renderPage();
    wrapper.find(".menu-button").simulate('click');
    assert.isTrue(store.getState().commonUi.drawerOpen);
  });

  [
    [false, false, 'user without admin permissions'],
    [true, true, 'user with admin permissions']
  ].forEach(([adminPermissionSetting, shouldShow, testDescriptor]) => {
    it(`video controls ${expect(shouldShow)} be shown for ${testDescriptor}`, async () => {
      collection.is_admin = adminPermissionSetting;
      let wrapper = await renderPage();
      assert.equal(wrapper.find("VideoCard").first().prop('isAdmin'), shouldShow);
    });
  });
});
