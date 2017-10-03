/* global SETTINGS: false */
// @flow
import { assert } from 'chai';
import _ from 'lodash';
import R from 'ramda';

import type { Action } from '../flow/reduxTypes';
import type { Store } from 'redux';

export function createAssertReducerResultState (store: Store, getReducerState: (x: any) => Object) {
  return (
    action: (arg: any) => Action<*,*>, stateLookup: (state: Object) => any, defaultValue: any
  ): void => {
    const getState = () => stateLookup(getReducerState(store.getState()));

    assert.deepEqual(defaultValue, getState());
    for (let value of [true, null, false, 0, 3, 'x', {'a': 'b'}, {}, [3, 4, 5], [], '']) {
      store.dispatch(action(value));
      assert.deepEqual(value, getState());
    }
  };
}

export const stringStrip = R.compose(R.join(" "), _.words);

export const makeCounter = (): (() => number) => {
  let gen = (function*() {
    let i = 1;
    while (true) {  // eslint-disable-line no-constant-condition
      yield i;
      i += 1;
    }
  })();
  // $FlowFixMe: Flow doesn't know that this always returns a number
  return () => gen.next().value;
};

// Helper method for test descriptions
export const expect = (expectation: boolean) => expectation ? "should" : "should not";
