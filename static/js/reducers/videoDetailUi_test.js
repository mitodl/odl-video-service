// @flow
import sinon from 'sinon';
import configureTestStore from "redux-asserts";
import { assert } from 'chai';

import rootReducer from '../reducers';
import {
  clearShareDialog,
  setShareDialogVisibility
} from '../actions/videoDetailUi';
import { createAssertReducerResultState } from "../util/test_utils";
import { INITIAL_UI_STATE } from "./videoDetailUi";

describe('VideoDetailUi', () => {
  let sandbox, assertReducerResultState, store;

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    store = configureTestStore(rootReducer);
    assertReducerResultState = createAssertReducerResultState(store, state => state.videoDetailUi);
  });

  afterEach(() => {
    sandbox.restore();
  });

  it('sets the share dialog visibility', () => {
    assertReducerResultState(setShareDialogVisibility, ui => ui.shareDialog.visible, false);
  });

  it('should clear the share dialog ui', () => {
    store.dispatch(clearShareDialog());
    assert.deepEqual(store.getState().videoDetailUi, INITIAL_UI_STATE);
  });
});
