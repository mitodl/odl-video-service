import { assert } from "chai"
import sinon from "sinon"

import suppressVictoryKeyWarning from "./suppressVictoryKeyWarning"

// A filter over console.error is only safe if it swallows exactly the one
// message it claims to. If it ever widened, real React warnings would stop
// failing the test run and nothing else would notice.
describe("suppressVictoryKeyWarning", () => {
  let sandbox, passedThrough, originalConsoleError

  // Exactly how React 16.14 calls console.error for this defect: a format
  // string with %s placeholders, the owner info, an empty child-owner slot,
  // and the component stack appended last.
  const victoryFormat =
    'Warning: Each child in a list should have a unique "key" prop.%s%s ' +
    "See https://fb.me/react-warning-keys for more information.%s"
  const victoryOwner = "\n\nCheck the render method of `VictoryAxis`."
  const victoryStack = "\n    in Axis\n    in VictoryAxis"
  const victoryArgs = [victoryFormat, victoryOwner, "", victoryStack]

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
    console.error(...victoryArgs)
    assert.lengthOf(passedThrough, 0)
  })

  it("passes through an unrelated console.error", () => {
    console.error("Warning: something actually broke")
    assert.deepEqual(passedThrough, [["Warning: something actually broke"]])
  })

  // The stack deliberately still names VictoryAxis: React appends it as the
  // last argument for anything rendered inside a chart, so a key warning
  // owned by a different component has to keep failing the run even then.
  it("passes through a key warning from another component", () => {
    const args = [
      victoryFormat,
      victoryOwner.replace("VictoryAxis", "VideoCard"),
      "",
      `\n    in VideoCard${victoryStack}`
    ]
    console.error(...args)
    assert.deepEqual(passedThrough, [args])
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
