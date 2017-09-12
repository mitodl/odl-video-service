// @flow
import React from 'react';
import sinon from 'sinon';
import { mount } from 'enzyme';
import { assert } from 'chai';
import { Provider } from 'react-redux';
import configureTestStore from 'redux-asserts';

import EditVideoFormDialog from './EditVideoFormDialog';

import rootReducer from '../../reducers';
import { actions } from '../../actions';
import {
  INIT_EDIT_VIDEO_FORM,
  initEditVideoForm,
  setEditVideoTitle,
  setEditVideoDesc,
} from '../../actions/commonUi';
import {
  setSelectedVideoKey
} from '../../actions/collectionUi';
import {
  INITIAL_UI_STATE
} from '../../reducers/commonUi';
import * as api from '../../lib/api';
import { makeVideo } from "../../factories/video";
import { makeCollection } from "../../factories/collection";

describe('EditVideoFormDialog', () => {
  let sandbox, store, listenForActions, hideDialogStub, video;
  let selectors = {
    SUBMIT_BTN: 'button.mdc-dialog__footer__button--accept',
    TITLE_INPUT: '#video-title',
    DESC_INPUT: '#video-description'
  };

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    store = configureTestStore(rootReducer);
    listenForActions = store.createListenForActions();
    hideDialogStub = sandbox.stub();
    video = makeVideo();
  });

  afterEach(() => {
    sandbox.restore();
  });

  const renderComponent = (props = {}) => {
    return mount(
      <Provider store={store}>
        <div>
          <EditVideoFormDialog
            open={true}
            hideDialog={hideDialogStub}
            video={video}
            commonUi={INITIAL_UI_STATE}
            { ...props }
          />
        </div>
      </Provider>
    );
  };

  it("initializes the form when given a video that doesn't match the current form key", async () => {
    let wrapper, previousFormState;
    store.dispatch(initEditVideoForm({key: 'mismatching-key'}));
    previousFormState = store.getState().commonUi.editVideoForm;
    await listenForActions([
      INIT_EDIT_VIDEO_FORM
    ], () => {
      wrapper = renderComponent();
    });
    if (!wrapper) throw "Render failed";

    assert.notEqual(previousFormState.key, store.getState().commonUi.editVideoForm.key);
    assert.equal(wrapper.find(selectors.TITLE_INPUT).prop('value'), video.title);
    assert.equal(wrapper.find(selectors.DESC_INPUT).prop('value'), video.description);
  });

  it("doesn't re-initialize the form when given a video that matches the current form key", () => {
    store.dispatch(initEditVideoForm({key: video.key}));
    let previousFormState = store.getState().commonUi.editVideoForm;
    renderComponent();
    assert.deepEqual(previousFormState, store.getState().commonUi.editVideoForm);
  });

  it('updates the video when the form is submitted', async () => {
    let wrapper;
    let updateVideoStub = sandbox.stub(api, 'updateVideo').returns(Promise.resolve(video));
    await listenForActions([
      INIT_EDIT_VIDEO_FORM
    ], () => {
      wrapper = renderComponent();
    });
    if (!wrapper) throw "Render failed";

    let newValues = {
      title: "New Title",
      description: "New Description"
    };
    store.dispatch(setEditVideoTitle(newValues.title));
    store.dispatch(setEditVideoDesc(newValues.description));
    await listenForActions([
      actions.videos.patch.requestType
    ], () => {
      // Calling onAccept directly b/c click doesn't work in JS tests due to MDC
      // $FlowFixMe: Flow... come on. 'wrapper' cannot be undefined at this point.
      wrapper.find('EditVideoFormDialog').find('Dialog').prop('onAccept')();
    });

    sinon.assert.calledWith(updateVideoStub, video.key, newValues);
  });

  it('can get a video from the collection state when no video is provided to the component directly', () => {
    let collection = makeCollection();
    let collectionVideo = collection.videos[0];
    store.dispatch(setSelectedVideoKey(collectionVideo.key));
    let wrapper = renderComponent({
      video: null,
      collection: collection
    });
    let dialogProps = wrapper.find('EditVideoFormDialog').props();
    assert.deepEqual(dialogProps.video, collectionVideo);
    assert.equal(dialogProps.shouldUpdateCollection, true);
  });

  it('prefers a video provided via props over a video in a collection', () => {
    let collection = makeCollection();
    let wrapper = renderComponent({
      video: video,
      collection: collection
    });
    let dialogProps = wrapper.find('EditVideoFormDialog').props();
    assert.deepEqual(dialogProps.video, video);
    assert.equal(dialogProps.shouldUpdateCollection, false);
  });
});