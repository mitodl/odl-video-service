import { assert } from "chai"

import suppressVendorLifecycleWarnings, {
  VENDOR_LIFECYCLE_WARNINGS
} from "./suppressVendorLifecycleWarnings"

// A filter over console.warn is only safe if it swallows exactly the messages
// it claims to. Its whole justification over a js_test.sh allowlist line is
// that it asserts the component list, so the tests that matter most here are
// the ones proving it STOPS matching when that list changes -- including if
// one of our own components ever joins it.
describe("suppressVendorLifecycleWarnings", () => {
  let passedThrough, originalConsoleWarn, restore

  // How react-dom actually calls console.warn: printWarning prepends
  // "Warning: " to the format string, whose trailing %s takes the sorted
  // component list as the single remaining argument.
  const warningArgs = (lifecycle, components) => [
    `Warning: ${lifecycle} has been renamed, and is not recommended for use. ` +
      "See https://fb.me/react-unsafe-component-lifecycles for details.\n\n" +
      "* Move code with side effects to componentDidMount, and set initial state in the constructor.\n" +
      `* Rename ${lifecycle} to UNSAFE_${lifecycle} to suppress this warning in non-strict mode.\n` +
      "\nPlease update the following components: %s",
    components
  ]

  beforeEach(() => {
    passedThrough = []
    // Stand in for the real console.warn before the helper captures it, so
    // whatever it lets through is recorded here instead of reaching the
    // actual test-run output. Note global_init.js has already installed this
    // helper once for the process; installing a second copy over the top is
    // harmless and is what makes this file self-contained.
    originalConsoleWarn = console.warn
    console.warn = (...args) => {
      passedThrough.push(args)
    }
    restore = suppressVendorLifecycleWarnings()
  })

  afterEach(() => {
    restore()
    console.warn = originalConsoleWarn
  })

  // One case per entry, so a failure names the dependency that moved.
  VENDOR_LIFECYCLE_WARNINGS.forEach(({ lifecycle, components }) => {
    it(`swallows the ${lifecycle} warning for ${components}`, () => {
      console.warn(...warningArgs(lifecycle, components))
      assert.lengthOf(passedThrough, 0)
    })
  })

  it("passes through an unrelated console.warn", () => {
    console.warn("Warning: something actually broke")
    assert.deepEqual(passedThrough, [["Warning: something actually broke"]])
  })

  // The self-policing property. A different component list means a component
  // React was not warning about before now uses a deprecated lifecycle --
  // possibly one of ours -- so the warning has to surface.
  it("passes through a known lifecycle with a different component list", () => {
    const args = warningArgs("componentWillMount", "VideoPlayer")
    console.warn(...args)
    assert.deepEqual(passedThrough, [args])
  })

  it("passes through a known list that has gained a component", () => {
    const args = warningArgs(
      "componentWillMount",
      "VictoryChart, VictoryStack, VideoPlayer"
    )
    console.warn(...args)
    assert.deepEqual(passedThrough, [args])
  })

  // componentWillUpdate is not in the table at all: nothing in the tree warns
  // about it today, so if something starts, that is news.
  it("passes through a lifecycle that is not in the table", () => {
    const args = warningArgs(
      "componentWillUpdate",
      "VictoryChart, VictoryStack"
    )
    console.warn(...args)
    assert.deepEqual(passedThrough, [args])
  })

  it("passes through a matching message with no component-list argument", () => {
    const [format] = warningArgs("componentWillMount", "VictoryChart")
    console.warn(format)
    assert.deepEqual(passedThrough, [[format]])
  })

  it("passes through a non-string first argument", () => {
    const error = new Error("boom")
    console.warn(error, "VictoryChart, VictoryStack")
    assert.deepEqual(passedThrough, [[error, "VictoryChart, VictoryStack"]])
  })

  // The suppressor is on console.warn only, so the per-file console.error
  // stubs elsewhere in the suite cannot shadow it and it cannot shadow them.
  it("leaves console.error alone", () => {
    const originalConsoleError = console.error
    const errors = []
    console.error = (...args) => {
      errors.push(args)
    }
    try {
      console.error(
        ...warningArgs("componentWillMount", "VictoryChart, VictoryStack")
      )
    } finally {
      console.error = originalConsoleError
    }
    assert.lengthOf(errors, 1)
  })
})
