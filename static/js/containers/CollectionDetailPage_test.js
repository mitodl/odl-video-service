// @flow
/* global SETTINGS: false */
import React from 'react';
import sinon from 'sinon';
import { mount } from 'enzyme';
import { assert } from 'chai';
import { Provider } from 'react-redux';
import configureTestStore from 'redux-asserts';

import CollectionDetailPage from './CollectionDetailPage';

import * as api from '../lib/api';
import { actions } from '../actions';
import {
  INIT_COLLECTION_FORM,
  SET_IS_NEW,
  SET_SELECTED_VIDEO_KEY,
} from "../actions/collectionUi";
import {
  HIDE_MENU,
  INIT_EDIT_VIDEO_FORM,
  SHOW_DIALOG,
  SHOW_MENU
} from "../actions/commonUi";
import rootReducer from '../reducers';
import { makeCollection } from "../factories/collection";
import { makeVideos } from "../factories/video";
import { expect } from "../util/test_utils";
import { DIALOGS } from "../constants";
import { makeInitializedForm } from "../lib/collection";

describe('CollectionDetailPage', () => {
  let sandbox, store, getCollectionStub, collection, listenForActions;
  let selectors = {
    TITLE: '.collection-detail-content h2',
    DESCRIPTION: 'p.description',
    MENU_BTN: '.menu-button',
    SETTINGS_BTN: '#edit-collection-button',
    DROPBOX_BTN: '.dropbox-btn',
    NO_VIDEOS_MSG: '.no-videos'
  };

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    store = configureTestStore(rootReducer);
    listenForActions = store.createListenForActions();
    collection = makeCollection();
    let collections = [makeCollection(), collection];

    getCollectionStub = sandbox.stub(api, 'getCollection').returns(Promise.resolve(collection));
    sandbox.stub(api, 'getCollections').returns(Promise.resolve(collections));
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
    if (!wrapper) throw new Error("Never will happen, make flow happy");
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

  it('shows a message when no videos have been added to the collection yet', async () => {
    collection.videos = [];
    let wrapper = await renderPage();
    let messageContainer = wrapper.find(selectors.NO_VIDEOS_MSG);
    assert.isTrue(messageContainer.exists());
    assert.include(messageContainer.text(), "You have not added any videos yet");
  });

  [
    ["Collection description", true, "non-empty description"],
    [null, false, "empty description"]
  ].forEach(([collectionDescription, shouldShow, testDescriptor]) => {
    it(`description ${expect(shouldShow)} be shown with ${testDescriptor}`, async () => {
      collection.description = collectionDescription;
      let wrapper = await renderPage();
      let descriptionEl = wrapper.find(selectors.DESCRIPTION);
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
      let titleText = wrapper.find(selectors.TITLE).text();
      assert.equal(titleText.indexOf(`(${videoCount})`) >= 0, shouldShow);
    });
  });

  it('has a toolbar whose handler will dispatch an action to open the drawer', async () => {
    let wrapper = await renderPage();
    wrapper.find(selectors.MENU_BTN).simulate('click');
    assert.isTrue(store.getState().commonUi.drawerOpen);
  });

  [
    [false, false, 'user without admin permissions'],
    [true, true, 'user with admin permissions']
  ].forEach(([adminPermissionSetting, shouldShow, testDescriptor]) => {
    it(`${expect(shouldShow)} render VideoCard with admin flag for ${testDescriptor}`, async () => {
      collection.is_admin = adminPermissionSetting;
      let wrapper = await renderPage();
      assert.equal(wrapper.find("VideoCard").first().prop('isAdmin'), shouldShow);
    });
  });

  [
    [false, false, 'user without admin permissions'],
    [true, true, 'user with admin permissions']
  ].forEach(([adminPermissionSetting, shouldShow, testDescriptor]) => {
    it(`${expect(shouldShow)} show dropbox upload & settings buttons for ${testDescriptor}`, async () => {
      collection.is_admin = adminPermissionSetting;
      let wrapper = await renderPage();
      assert.equal(wrapper.find(selectors.DROPBOX_BTN).exists(), shouldShow);
      assert.equal(wrapper.find(selectors.SETTINGS_BTN).exists(), shouldShow);
    });
  });

  it('uploads a video and reloads the collection page', async () => {
    let uploadVideoStub = sandbox.stub(api, 'uploadVideo').returns(Promise.resolve({}));
    let mockFiles = [{name: 'file1'}, {name: 'file2'}];
    collection.is_admin = true;
    let wrapper = await renderPage();

    await listenForActions([
      actions.uploadVideo.post.requestType,
      actions.uploadVideo.post.successType,
      actions.collections.get.requestType
    ], () => {
      wrapper.find('DropboxChooser').prop('success')(mockFiles);
    });

    sinon.assert.calledWith(uploadVideoStub, collection.key, mockFiles);
  });

  it('shows the edit video dialog', async () => {
    let wrapper = await renderPage();
    const state = await listenForActions([
      SET_SELECTED_VIDEO_KEY,
      SHOW_DIALOG,
      INIT_EDIT_VIDEO_FORM,
    ], () => {
      wrapper.find("VideoCard").first().prop('showEditDialog')();
    });

    const video = collection.videos[0];
    assert.equal(state.collectionUi.selectedVideoKey, video.key);
    assert.isTrue(state.commonUi.dialogVisibility[DIALOGS.EDIT_VIDEO]);
    assert.deepEqual(state.commonUi.editVideoForm, {
      description: video.description,
      key: video.key,
      title: video.title,
    });
  });

  it('shows the share video dialog', async () => {
    let wrapper = await renderPage();
    const state = await listenForActions([
      SET_SELECTED_VIDEO_KEY,
      SHOW_DIALOG,
    ], () => {
      wrapper.find("VideoCard").first().prop('showShareDialog')();
    });
    assert.equal(state.collectionUi.selectedVideoKey, collection.videos[0].key);
    assert.isTrue(state.commonUi.dialogVisibility[DIALOGS.SHARE_VIDEO]);
  });

  it('clicks the edit collection button', async () => {
    let wrapper = await renderPage();
    let eventStub = {
      preventDefault: sandbox.stub()
    };
    let state = await listenForActions([
      INIT_COLLECTION_FORM,
      SET_IS_NEW,
      SHOW_DIALOG,
    ], () => {
      wrapper.find("#edit-collection-button").prop('onClick')(eventStub);
    });
    sinon.assert.calledWith(eventStub.preventDefault);
    assert.isFalse(state.collectionUi.isNew);
    assert.deepEqual(state.collectionUi.editCollectionForm, makeInitializedForm(collection));
    assert.isTrue(state.commonUi.dialogVisibility[DIALOGS.COLLECTION_FORM]);
  });

  it('showVideoMenu sets menu visibility to true', async () => {
    let wrapper = await renderPage();
    const state = await listenForActions([
      SET_SELECTED_VIDEO_KEY,
      SHOW_MENU,
    ], () => {
      wrapper.find("VideoCard").first().prop('showVideoMenu')();
    });
    const video = collection.videos[0];
    assert.isTrue(state.commonUi.menuVisibility[video.key]);
  });

  it('closeVideoMenu sets menu visibility to false', async () => {
    let wrapper = await renderPage();
    const state = await listenForActions([
      SET_SELECTED_VIDEO_KEY,
      HIDE_MENU,
    ], () => {
      wrapper.find("VideoCard").first().prop('closeVideoMenu')();
    });
    const video = collection.videos[0];
    assert.isFalse(state.commonUi.menuVisibility[video.key]);
  });

});
