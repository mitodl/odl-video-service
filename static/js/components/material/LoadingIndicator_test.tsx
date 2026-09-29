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

    // The wrapper, the modifier and the role are all the OUTER element. The
    // animation @material/linear-progress supplies is keyframed on the inner
    // bars -- .mdc-linear-progress__primary-bar and __secondary-bar, each
    // with a __bar-inner -- so without these four assertions the children
    // could all be deleted and every check above would still pass, leaving a
    // static empty div that reports itself as an indeterminate progressbar.
    for (const cls of [
      "mdc-linear-progress__buffering-dots",
      "mdc-linear-progress__buffer",
      "mdc-linear-progress__primary-bar",
      "mdc-linear-progress__secondary-bar"
    ]) {
      assert.isNotNull(
        bar.querySelector(`.${cls}`),
        `expected an .${cls} inside .mdc-linear-progress`
      )
    }

    // Both animated bars carry the inner span MDC translates; one of the two
    // missing it is the asymmetric case a single querySelector would miss.
    for (const cls of [
      "mdc-linear-progress__primary-bar",
      "mdc-linear-progress__secondary-bar"
    ]) {
      const animated = bar.querySelector(`.${cls}`)
      assert.isTrue(
        animated.classList.contains("mdc-linear-progress__bar"),
        `expected .${cls} to also carry .mdc-linear-progress__bar`
      )
      assert.isNotNull(
        animated.querySelector(".mdc-linear-progress__bar-inner"),
        `expected a .mdc-linear-progress__bar-inner inside .${cls}`
      )
    }
  })
})
