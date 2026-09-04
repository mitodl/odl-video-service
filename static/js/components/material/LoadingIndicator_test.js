import React from "react"
import { assert } from "chai"
import { render } from "@testing-library/react"

import LoadingIndicator from "./LoadingIndicator"

describe("LoadingIndicator", () => {
  it("renders a label and an indeterminate linear progress bar", () => {
    const { container } = render(<LoadingIndicator />)

    const root = container.querySelector(".loading-indicator")
    assert.isNotNull(root, "expected a .loading-indicator root")
    assert.equal(root.querySelector("label").textContent, "Loading...")

    // The MDC linear-progress contract: an indeterminate bar carries both the
    // base class and the indeterminate modifier, and exposes progressbar
    // semantics. rmwc used to generate this; we now own it.
    const bar = root.querySelector(".mdc-linear-progress")
    assert.isNotNull(bar, "expected an .mdc-linear-progress element")
    assert.isTrue(bar.classList.contains("mdc-linear-progress--indeterminate"))
    assert.equal(bar.getAttribute("role"), "progressbar")
  })
})
