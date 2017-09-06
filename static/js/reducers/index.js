// @flow
import { combineReducers } from 'redux';
import { deriveReducers } from "redux-hammock";

import { actions } from "../actions";
import { endpoints } from "../lib/redux_rest";
import videoDetailUi from './videoDetailUi';
import commonUi from './commonUi';

const reducers: Object = {
  videoDetailUi,
  commonUi
};
endpoints.forEach(endpoint => {
  reducers[endpoint.name] = deriveReducers(endpoint, actions[endpoint.name]);
});

export default combineReducers({
  ...reducers,
});
