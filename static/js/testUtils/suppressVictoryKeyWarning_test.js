import { assert } from "chai"
import sinon from "sinon"

import suppressVictoryKeyWarning from "./suppressVictoryKeyWarning"

// A filter over console.error is only safe if it swallows exactly the one
// message it claims to. If it ever widened, real React warnings would stop
// failing the test run and nothing else would notice.
describe("suppressVictoryKeyWarning", () => {
  let sandbox, passedThrough, originalConsoleError

  const victoryMessage =
    'Warning: Each child in an array or iterator should have a unique "key" ' +
    "prop. Check the render method of `VictoryAxis`."

  beforeEach(() => {
    passedThrough = []
    // Stand in for the real console.error before the helper captures it, so
    // whatever it lets through is recorded here instead of reaching the
    // actual test-run output. Swapped by hand rather than with sinon: the
    // helper stubs the same method, and sinon refuses to wrap it twice.
    originalConsoleError = console.error
    console.error = (...args) => {
      passedThrough.push(args)
    }
    sandbox = sinon.createSandbox()
    suppressVictoryKeyWarning(sandbox)
  })

  afterEach(() => {
    sandbox.restore()
    console.error = originalConsoleError
  })

  it("swallows Victory's key warning", () => {
    console.error(victoryMessage)
    assert.lengthOf(passedThrough, 0)
  })

  it("passes through an unrelated console.error", () => {
    console.error("Warning: something actually broke")
    assert.deepEqual(passedThrough, [["Warning: something actually broke"]])
  })

  it("passes through a key warning from another component", () => {
    const message = victoryMessage.replace("VictoryAxis", "VideoCard")
    console.error(message)
    assert.deepEqual(passedThrough, [[message]])
  })

  it("passes through an unrelated VictoryAxis warning", () => {
    console.error("Warning: VictoryAxis received an invalid prop")
    assert.deepEqual(passedThrough, [
      ["Warning: VictoryAxis received an invalid prop"]
    ])
  })

  it("passes through a non-string first argument", () => {
    const error = new Error("boom")
    console.error(error)
    assert.deepEqual(passedThrough, [[error]])
  })

  it("forwards every argument, not just the message", () => {
    console.error("Warning: broke", "extra", 42)
    assert.deepEqual(passedThrough, [["Warning: broke", "extra", 42]])
  })
})
