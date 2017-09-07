// @flow
import sinon from 'sinon';
import configureTestStore from "redux-asserts";
import { assert } from 'chai';

import rootReducer from '../reducers';
import { setDrawerOpen } from '../actions/commonUi';
import { createAssertReducerResultState } from "../util/test_utils";
import { INITIAL_UI_STATE } from "./commonUi";

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

  it('Should open the drawer in the UI', () => {
    store.dispatch(setDrawerOpen(true));
    assert.deepEqual(store.getState().commonUi, {drawerOpen: true});
  });

  it('Should close the drawer in the UI', () => {
    store.dispatch(setDrawerOpen(false));
    assert.deepEqual(store.getState().commonUi, INITIAL_UI_STATE);
  });

  it('setting the drawer visibility changes state', () => {
    assertReducerResultState(setDrawerOpen, ui => ui.drawerOpen, false);
  });
});
