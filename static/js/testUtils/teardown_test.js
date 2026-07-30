import React from "react"
import { assert } from "chai"
import { render } from "@testing-library/react"

let unmountCount = 0

class UnmountRecorder extends React.Component {
  componentWillUnmount() {
    unmountCount += 1
  }

  render() {
    return <div>mounted</div>
  }
}

describe("global teardown", () => {
  it("mounts a component and lets the afterEach hook run", () => {
    render(<UnmountRecorder />)
    assert.equal(unmountCount, 0)
  })

  it("unmounted the previous test's tree before this test started", () => {
    assert.equal(
      unmountCount,
      1,
      "componentWillUnmount did not fire -- global_init.js wiped the DOM " +
        "before RTL could unmount, so cleanup is not running"
    )
  })
})
