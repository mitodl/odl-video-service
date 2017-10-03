// @flow
import { combineReducers } from 'redux';
import { deriveReducers } from "redux-hammock";

import { actions } from "../actions";
import { endpoints } from "../lib/redux_rest";
import commonUi from './commonUi';
import collectionUi from './collectionUi';
import videoSubtitleUi from "./videoSubtitleUi";

const reducers: Object = {
  commonUi,
  collectionUi,
  videoSubtitleUi
};
endpoints.forEach(endpoint => {
  reducers[endpoint.name] = deriveReducers(endpoint, actions[endpoint.name]);
});

export default combineReducers({
  ...reducers,
});
