// @flow
import { assert } from "chai";
import sinon from "sinon";
import { INITIAL_STATE } from "redux-hammock/constants";
import configureTestStore from "redux-asserts";
import * as api from "../lib/api";

import rootReducer from "../reducers";
import { actions } from "../actions";
import { makeVideoSubtitle } from "../factories/video";

describe("videos endpoint", () => {
  let store, sandbox, dispatchThen, createSubtitleStub, deleteSubtitleStub;

  beforeEach(() => {
    store = configureTestStore(rootReducer);
    dispatchThen = store.createDispatchThen();
    sandbox = sinon.sandbox.create();
    createSubtitleStub = sandbox.stub(api, "createSubtitle").throws();
    deleteSubtitleStub = sandbox.stub(api, "deleteSubtitle").throws();
  });

  afterEach(() => {
    sandbox.restore();
  });

  it("should have some initial state", () => {
    assert.deepEqual(store.getState().videoSubtitles, {...INITIAL_STATE, data: new Map()});
  });

  it("should create subtitles", async () => {
    const subtitle = makeVideoSubtitle();
    createSubtitleStub.returns(Promise.resolve(subtitle));
    const payload = new FormData();
    payload.append("collection_key", "fake-key");
    payload.append("video", "fake-key");
    // $FlowFixMe
    payload.append("file", [{"name": "foo", data: ""}]);
    await dispatchThen(
      actions.videoSubtitles.post(payload),
      [
        actions.videoSubtitles.post.requestType,
        actions.videoSubtitles.post.successType,
      ]
    );
    sinon.assert.calledWith(createSubtitleStub, payload);
  });

  it("should delete subtitles", async () => {
    const subtitle = makeVideoSubtitle();
    deleteSubtitleStub.returns(Promise.resolve({}));
    await dispatchThen(
      actions.videoSubtitles.delete(subtitle.id),
      [
        actions.videoSubtitles.delete.requestType,
        actions.videoSubtitles.delete.successType,
      ]
    );
    sinon.assert.calledWith(deleteSubtitleStub, subtitle.id);
  });
});
