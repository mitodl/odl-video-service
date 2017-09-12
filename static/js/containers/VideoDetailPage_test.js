// @flow
import React from 'react';
import sinon from 'sinon';
import moment from 'moment';
import { mount } from 'enzyme';
import { assert } from 'chai';
import { Provider } from 'react-redux';
import configureTestStore from 'redux-asserts';

import VideoDetailPage from './VideoDetailPage';

import * as api from '../lib/api';
import { actions } from '../actions';
import rootReducer from '../reducers';
import { makeVideo } from '../factories/video';
import { makeCollectionUrl } from "../lib/urls";
import {
  MM_DD_YYYY,
  VIDEO_STATUS_TRANSCODING,
  VIDEO_STATUS_ERROR,
} from "../constants";

import type { Video } from "../flow/videoTypes";

describe('VideoDetailPage', () => {
  let sandbox, store, getVideoStub, video: Video, listenForActions;
  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    store = configureTestStore(rootReducer);
    listenForActions = store.createListenForActions();
    video = makeVideo();

    getVideoStub = sandbox.stub(api, 'getVideo').returns(Promise.resolve(video));
  });

  afterEach(() => {
    sandbox.restore();
  });

  const renderPage = async (props = {}) => {
    let wrapper;
    await listenForActions([
      actions.videos.get.requestType,
      actions.videos.get.successType,
    ], () => {
      wrapper = mount(
        <Provider store={store}>
          <VideoDetailPage
            videoKey={video.key}
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

  it('fetches requirements on load', async () => {
    await renderPage();
    sinon.assert.calledWith(getVideoStub, video.key);
  });

  it('renders the video player', async () => {
    let wrapper = await renderPage();
    assert.deepEqual(wrapper.find("VideoPlayer").props(), {
      video: video,
      useIframeForUSwitch: true,
    });
  });

  it('shows the video title, description and upload date, and link to collection', async () => {
    let wrapper = await renderPage();
    assert.equal(wrapper.find(".video-title").text(), video.title);
    assert.equal(wrapper.find(".video-description").text(), video.description);
    const formatted = moment(video.created_at).format(MM_DD_YYYY);
    assert.equal(wrapper.find(".upload-date").text(), `Uploaded ${formatted}`);
    let link = wrapper.find(".collection-link");
    assert.equal(link.props().href, makeCollectionUrl(video.collection_key));
    assert.equal(link.text(), video.collection_title);
  });

  it('shows an error message if in an error state', async () => {
    video.status = VIDEO_STATUS_TRANSCODING;
    let wrapper = await renderPage();
    assert.equal(wrapper.find(".video-message").text(),
      "Video is processing, check back later"
    );
  });

  it('indicates video is processing if it, well, is', async () => {
    video.status = VIDEO_STATUS_ERROR;
    let wrapper = await renderPage();
    assert.equal(wrapper.find(".video-message").text(),
      "Something went wrong :("
    );
  });

  it('includes the share button and dialog', async () => {
    let wrapper = await renderPage();
    assert.isTrue(wrapper.find(".share").exists());
    assert.isTrue(wrapper.find("ShareVideoDialog").exists());
  });

  it('includes the edit button and dialog when the user has correct permissions', async () => {
    let wrapper = await renderPage({editable: true});
    assert.isTrue(wrapper.find(".edit").exists());
    assert.isTrue(wrapper.find("EditVideoFormDialog").exists());
  });

  it("edit button doesn't appear if video is not editable", async () => {
    let wrapper = await renderPage();
    assert.isFalse(wrapper.find(".edit").exists());
  });

  it('has a toolbar whose handler will dispatch an action to open the drawer', async () => {
    let wrapper = await renderPage();
    wrapper.find(".menu-button").simulate('click');
    assert.isTrue(store.getState().commonUi.drawerOpen);
  });
});
