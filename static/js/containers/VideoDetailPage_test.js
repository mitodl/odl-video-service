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
import {
  CLEAR_EDIT_DIALOG,
  SET_EDIT_DIALOG_VISIBILITY,
  SET_TITLE,
  SET_DESCRIPTION,
  SET_SHARE_DIALOG_VISIBILITY,
  CLEAR_SHARE_DIALOG
} from '../actions/videoDetailUi';
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
  let sandbox, store, getVideoStub, updateVideoStub, video: Video, listenForActions;
  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    store = configureTestStore(rootReducer);
    listenForActions = store.createListenForActions();
    video = makeVideo();

    getVideoStub = sandbox.stub(api, 'getVideo').returns(Promise.resolve(video));
    updateVideoStub = sandbox.stub(api, 'updateVideo').throws();
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

  it('opens the dialog when the edit button is clicked and video is editable', async () => {
    let wrapper = await renderPage({editable: true});
    assert.isFalse(wrapper.find(".edit").props().disabled);
    wrapper.find(".edit").props().onClick();
    assert.isTrue(store.getState().videoDetailUi.editDialog.visible);
  });

  it('edit button has no effect if video is not editable', async () => {
    let wrapper = await renderPage();
    assert.isTrue(wrapper.find(".edit").props().disabled);
  });

  it('edits the title and description and submits the data to trigger an update', async () => {
    let wrapper = await renderPage({editable: true});

    const newTitle = 'new title';
    const newDescription = "omg this is the BEST VIDEO";
    const expectedVideo = {
      ...video,
      title: newTitle,
    };
    updateVideoStub.returns(Promise.resolve(expectedVideo));
    await listenForActions([
      actions.videos.patch.requestType,
      actions.videos.patch.successType,
      SET_EDIT_DIALOG_VISIBILITY,
      SET_DESCRIPTION,
      SET_DESCRIPTION,
      SET_TITLE,
      SET_TITLE,
      CLEAR_EDIT_DIALOG,
    ], () => {
      wrapper.find(".edit").props().onClick();
      wrapper.find("#video-title").props().onChange({target: {value: newTitle}});
      wrapper.find("#video-description").props().onChange({target: {value: newDescription}});
      wrapper.find('Dialog').at(0).props().onAccept();
    });

    assert.deepEqual(store.getState().videos.data.get(expectedVideo.key), expectedVideo);
    sinon.assert.calledWith(updateVideoStub, video.key, {
      title: newTitle,
      description: newDescription,
    });
  });

  it('show the share dialog', async () => {
    let wrapper = await renderPage({editable: true});
    await listenForActions([
      SET_SHARE_DIALOG_VISIBILITY,
      CLEAR_SHARE_DIALOG,
    ], () => {
      wrapper.find(".share").props().onClick();
      assert.equal(wrapper.find("#video-url").props().value, `http://fake/videos/${video.key}/embed/`);
      wrapper.find("Dialog").at(1).props().onCancel();
    });
  });

  it('share dialog shows the correct content', async () => {
    let wrapper = await renderPage({editable: true});
    wrapper.find(".share").props().onClick();
    assert.equal(wrapper.find("#video-url").props().value, `http://fake/videos/${video.key}/embed/`);
    assert.isTrue(wrapper.find("#video-embed-code").props().value.startsWith(
      `<iframe src="http://fake/videos/${video.key}/embed/"`));
    wrapper.find("Dialog").at(1).props().onCancel();
  });

  it('has a toolbar whose handler will dispatch an action to open the drawer', async () => {
    let wrapper = await renderPage();
    wrapper.find(".menu-button").simulate('click');
    assert.isTrue(store.getState().commonUi.drawerOpen);
  });
});
