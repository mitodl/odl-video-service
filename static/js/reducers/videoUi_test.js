// @flow
import { assert } from "chai";
import configureTestStore from "redux-asserts";

import rootReducer from "../reducers";
import { INITIAL_UPLOAD_SUBTITLE_FORM_STATE } from "./videoUi";
import { setUploadSubtitle } from "../actions/videoUi";

describe("videoUi", () => {
  let store;

  beforeEach(() => {
    store = configureTestStore(rootReducer);
  });

  it("has some initial state", () => {
    assert.deepEqual(store.getState().videoUi, {
      videoSubtitleForm: INITIAL_UPLOAD_SUBTITLE_FORM_STATE,
      corner: "upperLeft"
    });
  });

  it("has action that sets the file to upload", () => {
    assert.deepEqual(store.getState().videoUi.videoSubtitleForm, INITIAL_UPLOAD_SUBTITLE_FORM_STATE);
    let fileUpload = {"name": "foo.vtt", "data": "ddd"};
    store.dispatch(setUploadSubtitle(fileUpload));
    assert.equal(store.getState().videoUi.videoSubtitleForm.subtitle, fileUpload);
  });
});
