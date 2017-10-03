// @flow
import { assert } from "chai";
import configureTestStore from "redux-asserts";

import rootReducer from "../reducers";
import { INITIAL_UPLOAD_SUBTITLE_FORM_STATE } from "./videoSubtitleUi";
import { setUploadSubtitle } from "../actions/videoSubtitleUi";

describe("videoSubtitleUi", () => {
  let store;

  beforeEach(() => {
    store = configureTestStore(rootReducer);
  });

  it("has some initial state", () => {
    assert.deepEqual(store.getState().videoSubtitleUi, {
      videoSubtitleForm: INITIAL_UPLOAD_SUBTITLE_FORM_STATE
    });
  });

  it("has action that sets the file to upload", () => {
    assert.deepEqual(store.getState().videoSubtitleUi.videoSubtitleForm, INITIAL_UPLOAD_SUBTITLE_FORM_STATE);
    let fileUpload = {"name": "foo.vtt", "data": "ddd"};
    store.dispatch(setUploadSubtitle(fileUpload));
    assert.equal(store.getState().videoSubtitleUi.videoSubtitleForm.subtitle, fileUpload);
  });
});
