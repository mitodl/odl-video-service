// @flow
import React from "react"
import sinon from "sinon"
import { render, fireEvent, waitFor } from "@testing-library/react"
import { assert } from "chai"

import DescriptionField from "./DescriptionField"
import {
  DESCRIPTION_FORMAT_HTML,
  DESCRIPTION_FORMAT_TEXT
} from "../../constants"

describe("DescriptionField", () => {
  let onChange, onUpgrade

  const renderField = (props = {}) =>
    render(
      <DescriptionField
        label="Description"
        id="test-desc"
        value=""
        descriptionFormat={DESCRIPTION_FORMAT_TEXT}
        onChange={onChange}
        onUpgrade={onUpgrade}
        {...props}
      />
    )

  const textarea = (container: HTMLElement) =>
    container.querySelector("textarea")

  const upgradeButton = (container: HTMLElement) =>
    container.querySelector(".description-upgrade__button")

  beforeEach(() => {
    onChange = sinon.stub()
    onUpgrade = sinon.stub()
  })

  describe("a description still stored as plain text", () => {
    it("gets a textarea rather than the rich-text editor", async () => {
      const { container } = renderField({ value: "line one\nline two" })
      assert.isNotNull(textarea(container))
      assert.equal(textarea(container).value, "line one\nline two")
      /*
       * Opening plain text in the rich-text editor would parse it as HTML and
       * collapse every line break the author typed; saving would then make that
       * loss permanent. Hence the textarea until they ask to upgrade.
       */
      await waitFor(() =>
        assert.isNull(container.querySelector(".ProseMirror"))
      )
    })

    it("reports what is typed verbatim", () => {
      const { container } = renderField({ value: "old" })
      fireEvent.change(textarea(container), {
        target: { value: "new <b to a" }
      })
      sinon.assert.calledWith(onChange, "new <b to a")
    })

    it("labels the textarea", () => {
      const { container } = renderField()
      assert.equal(container.querySelector("label").textContent, "Description")
      assert.equal(
        container.querySelector("label").getAttribute("for"),
        "test-desc"
      )
      assert.equal(textarea(container).id, "test-desc")
    })

    it("offers the upgrade, and says why the field looks plain", () => {
      const { container } = renderField()
      assert.isNotNull(upgradeButton(container))
      assert.include(
        container.querySelector(".description-upgrade__hint").textContent,
        "plain text"
      )
    })

    it("asks its parent to upgrade rather than converting anything itself", () => {
      // The conversion is the server's (ui.html.upgrade_description); nothing
      // here reimplements escaping.
      const { container } = renderField({ value: "some text" })
      fireEvent.click(upgradeButton(container))
      sinon.assert.calledOnce(onUpgrade)
      sinon.assert.notCalled(onChange)
    })

    it("disables the upgrade while one is in flight", () => {
      const { container } = renderField({ upgrading: true })
      assert.isTrue(upgradeButton(container).disabled)
    })

    it("shows an upgrade that failed", () => {
      const { container } = renderField({ upgradeError: "Could not convert." })
      assert.equal(
        container.querySelector(".description-upgrade__error").textContent,
        "Could not convert."
      )
    })

    it("has nothing to report when the upgrade has not failed", () => {
      const { container } = renderField()
      assert.isNull(container.querySelector(".description-upgrade__error"))
    })
  })

  describe("a description already stored as rich text", () => {
    it("gets the rich-text editor", async () => {
      const { container } = renderField({
        value:             "<p>already <strong>rich</strong></p>",
        descriptionFormat: DESCRIPTION_FORMAT_HTML
      })
      // The editor engine is a split chunk, so it arrives after mount.
      await waitFor(() =>
        assert.isNotNull(container.querySelector(".ProseMirror"))
      )
      assert.include(
        container.querySelector(".ProseMirror").innerHTML,
        "<strong>rich</strong>"
      )
    })

    it("has no textarea and no upgrade offer", async () => {
      const { container } = renderField({
        value:             "<p>x</p>",
        descriptionFormat: DESCRIPTION_FORMAT_HTML
      })
      await waitFor(() =>
        assert.isNotNull(container.querySelector(".ProseMirror"))
      )
      assert.isNull(textarea(container))
      assert.isNull(upgradeButton(container))
    })

    it("reports edits as HTML", async () => {
      const { container } = renderField({
        value:             "<p>x</p>",
        descriptionFormat: DESCRIPTION_FORMAT_HTML
      })
      await waitFor(() =>
        assert.isNotNull(container.querySelector(".ProseMirror"))
      )
      fireEvent.click(
        container.querySelector('button[aria-label="Bulleted list"]')
      )
      await waitFor(() => sinon.assert.called(onChange))
      assert.include(onChange.lastCall.args[0], "<ul>")
    })
  })
})
