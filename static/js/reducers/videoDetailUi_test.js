// @flow
import sinon from 'sinon';
import configureTestStore from "redux-asserts";
import { assert } from 'chai';

import rootReducer from '../reducers';
import {
  clearEditDialog,
  clearShareDialog,
  setEditDialogVisibility,
  setShareDialogVisibility,
  setDrawerOpen,
  setTitle,
  setDescription,
} from '../actions/videoDetailUi';
import { createAssertReducerResultState } from "../util/test_utils";
import { INITIAL_UI_STATE } from "./videoDetailUi";

describe('videoDetailUi', () => {
  let sandbox, assertReducerResultState, store;

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    assertReducerResultState = createAssertReducerResultState(store, state => state.videoDetailUi);
    store = configureTestStore(rootReducer);
  });

  afterEach(() => {
    sandbox.restore();
  });

  it('should clear the edit dialog ui', () => {
    store.dispatch(setTitle("something"));
    store.dispatch(clearEditDialog());
    assert.deepEqual(store.getState().videoDetailUi, INITIAL_UI_STATE);
  });

  it('sets the title', () => {
    assertReducerResultState(setTitle, ui => ui.editDialog.title, '');
  });

  it('sets the description', () => {
    assertReducerResultState(setDescription, ui => ui.editDialog.description, '');
  });


  it('sets the edit dialog visibility', () => {
    assertReducerResultState(setEditDialogVisibility, ui => ui.editDialog.visible, false);
  });

  it('sets the share dialog visibility', () => {
    assertReducerResultState(setShareDialogVisibility, ui => ui.shareDialog.visible, false);
  });

  it('should clear the share dialog ui', () => {
    store.dispatch(clearShareDialog());
    assert.deepEqual(store.getState().videoDetailUi, INITIAL_UI_STATE);
  });

  it('sets the drawer visibility', () => {
    assertReducerResultState(setDrawerOpen, ui => ui.drawerOpen, false);
  });
});
