// @flow
import sinon from 'sinon';
import configureTestStore from "redux-asserts";
import { assert } from 'chai';

import rootReducer from '../reducers';
import {
  setDrawerOpen,
  setEditVideoTitle,
  setEditVideoDesc,
  initEditVideoForm
} from '../actions/commonUi';
import { createAssertReducerResultState } from "../util/test_utils";
import { INITIAL_UI_STATE, INITIAL_EDIT_VIDEO_FORM_STATE } from "./commonUi";

describe('CommonUi', () => {
  let sandbox, assertReducerResultState, store;

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    assertReducerResultState = createAssertReducerResultState(store, state => state.commonUi);
    store = configureTestStore(rootReducer);
  });

  afterEach(() => {
    sandbox.restore();
  });

  it('should open the drawer in the UI', () => {
    store.dispatch(setDrawerOpen(true));
    assert.include(store.getState().commonUi, {drawerOpen: true});
  });

  it('should close the drawer in the UI', () => {
    store.dispatch(setDrawerOpen(false));
    assert.deepEqual(store.getState().commonUi, INITIAL_UI_STATE);
  });

  it('setting the drawer visibility changes state', () => {
    assertReducerResultState(setDrawerOpen, ui => ui.drawerOpen, false);
  });

  it('has actions that set video title and description', () => {
    assert.deepEqual(store.getState().commonUi.editVideoForm, INITIAL_EDIT_VIDEO_FORM_STATE);
    store.dispatch(setEditVideoTitle('title'));
    store.dispatch(setEditVideoDesc('description'));
    assert.equal(store.getState().commonUi.editVideoForm.title, 'title');
    assert.equal(store.getState().commonUi.editVideoForm.description, 'description');
  });

  it('has an action that initializes the edit video form,', () => {
    let formObj = {key: 'key', title: 'title', description: 'description'};
    store.dispatch(initEditVideoForm(formObj));
    assert.deepEqual(store.getState().commonUi.editVideoForm, formObj);
  });
});
