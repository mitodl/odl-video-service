// @flow
import sinon from 'sinon';
import configureTestStore from "redux-asserts";
import { assert } from 'chai';
import _ from 'lodash';

import rootReducer from '../reducers';
import {
  setDrawerOpen,
  setEditVideoTitle,
  setEditVideoDesc,
  initEditVideoForm,
  showDialog,
  hideDialog
} from '../actions/commonUi';
import { INITIAL_UI_STATE, INITIAL_EDIT_VIDEO_FORM_STATE } from "./commonUi";
import { createAssertReducerResultState } from "../util/test_utils";
import { DIALOGS } from "../constants";

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

  it('has actions that open and close dialogs', () => {
    _.mapKeys(DIALOGS, (dialogKey) => {
      store.dispatch(showDialog(dialogKey));
      assert.deepEqual(store.getState().commonUi.dialogVisibility[dialogKey], true);
      store.dispatch(hideDialog(dialogKey));
      assert.deepEqual(store.getState().commonUi.dialogVisibility[dialogKey], false);
    });
  });
});
