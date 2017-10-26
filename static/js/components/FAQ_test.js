// @flow
/* global SETTINGS:false */
import React from "react";
import sinon from "sinon";
import { shallow } from "enzyme";
import { assert } from "chai";

import FAQ from "./FAQ";

import { adminFAQs, viewerFAQs } from "../data/faqs";

describe("FAQ Component", () => {
  let FAQVisibility, toggleFAQVisibility;
  beforeEach(() => {
    FAQVisibility = new Map();
    toggleFAQVisibility = sinon.stub();
  });

  const renderFAQs = () => shallow(<FAQ FAQVisibility={FAQVisibility} toggleFAQVisibility={toggleFAQVisibility} />);

  it("shows the appropriate FAQs to the user", () => {
    [true, false].forEach(isAdmin => {
      SETTINGS.is_admin = isAdmin;
      const wrapper = renderFAQs();
      const questions = wrapper
        .find(".show-hide-question")
        .map(wrapper =>
          wrapper
            .find("div")
            .at(1)
            .text()
        );
      assert.deepEqual(questions, Object.keys(isAdmin ? adminFAQs : viewerFAQs));
    });
  });

  it("calls the toggleFAQVisibility callback when a question title is clicked", () => {
    const wrapper = renderFAQs();
    wrapper.find(".show-hide-question").at(0).simulate("click");
    assert(toggleFAQVisibility.called);
  });

  it("checks FAQVisibility to see if a question should be open", () => {
    Object.entries(viewerFAQs).forEach(([question, answer]) => {
      [true, false].forEach(visibility => {
        FAQVisibility.set(question, visibility);
        const wrapper = renderFAQs();
        if (visibility) {
          assert.equal(wrapper.find(".answer").text(), answer);
        } else {
          assert.lengthOf(wrapper.find(".answer"), 0);
        }
      });
    });
  });
});
