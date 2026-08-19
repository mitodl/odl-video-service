import React from "react"
import { assert } from "chai"
import { render } from "@testing-library/react"

import { makeUnmountRecorder } from "./unmountRecorder"
import { resetTestEnvironment } from "../global_init"

describe("global teardown", () => {
  it("unmounts the RTL tree when the shared afterEach hook runs", () => {
    const { UnmountRecorder, getUnmountCount } = makeUnmountRecorder()

    render(<UnmountRecorder />)
    assert.equal(getUnmountCount(), 0)

    // Call the exact function mocha's afterEach hook invokes, rather than
    // relying on running a second `it` block after this one -- that would
    // pass or fail depending on whether this file is run in isolation.
    resetTestEnvironment()

    assert.equal(
      getUnmountCount(),
      1,
      "componentWillUnmount did not fire -- global_init.js wiped the DOM " +
        "before RTL could unmount, so cleanup is not running"
    )
  })
})
