// @flow
import sinon from 'sinon';
import configureTestStore from "redux-asserts";
import { assert } from 'chai';

import rootReducer from '../reducers';
import {
  clearDialog,
  setDialogVisibility,
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

  it('should clear the ui', () => {
    store.dispatch(setTitle("something"));
    store.dispatch(clearDialog());
    assert.deepEqual(store.getState().videoDetailUi, INITIAL_UI_STATE);
  });

  it('sets the title', () => {
    assertReducerResultState(setTitle, ui => ui.dialog.title, '');
  });

  it('sets the description', () => {
    assertReducerResultState(setDescription, ui => ui.dialog.description, '');
  });


  it('sets the dialog visibility', () => {
    assertReducerResultState(setDialogVisibility, ui => ui.dialog.visible, false);
  });

  it('sets the drawer visibility', () => {
    assertReducerResultState(setDrawerOpen, ui => ui.drawerOpen, false);
  });
});
