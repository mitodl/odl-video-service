import { assert } from "chai"

import suppressVendorLifecycleWarnings, {
  VENDOR_LIFECYCLE_WARNINGS
} from "./suppressVendorLifecycleWarnings"

/**
 * A filter over console.warn is only safe if it swallows exactly the messages
 * it claims to, and its justification over a js_test.sh allowlist line is that
 * it asserts which components it will excuse. So these tests must be able to
 * detect the table drifting -- which an earlier version could not, because it
 * was driven by the exported table and therefore asserted the table against
 * itself. A deliberately wrong entry left all its cases passing.
 *
 * Everything expected is therefore written out LITERALLY below, independent of
 * suppressVendorLifecycleWarnings.js: the two format strings are copied
 * verbatim from react-dom 16.14.0 (cjs/react-dom.development.js lines 11371
 * and 11377), and EXPECTED_TABLE is a hand-maintained copy of the suppression
 * table.
 *
 * That duplication is deliberate and it IS the check. Do not DRY it up by
 * importing the table and deriving the expectations from it -- that is exactly
 * the tautology this file exists to avoid. Any edit to the real table has to
 * be made here too, which is the point: it cannot happen silently.
 *
 * TASK 7 of this PR removes victory, and must delete the two victory rows from
 * EXPECTED_TABLE and their two suppression cases below, alongside the same
 * deletions in the helper and the ledger cap move 6 -> 4.
 */

// Copied verbatim from react-dom 16.14.0. Includes the "Warning: " prefix that
// printWarning prepends and the trailing %s that takes the component list.
const CWM =
  "Warning: componentWillMount has been renamed, and is not recommended for use. See https://fb.me/react-unsafe-component-lifecycles for details.\n\n* Move code with side effects to componentDidMount, and set initial state in the constructor.\n* Rename componentWillMount to UNSAFE_componentWillMount to suppress this warning in non-strict mode. In React 17.x, only the UNSAFE_ name will work. To rename all deprecated lifecycles to their new names, you can run `npx react-codemod rename-unsafe-lifecycles` in your project source folder.\n\nPlease update the following components: %s"

const CWRP =
  "Warning: componentWillReceiveProps has been renamed, and is not recommended for use. See https://fb.me/react-unsafe-component-lifecycles for details.\n\n* Move data fetching code or side effects to componentDidUpdate.\n* If you're updating state whenever props change, refactor your code to use memoization techniques or move it to static getDerivedStateFromProps. Learn more at: https://fb.me/react-derived-state\n* Rename componentWillReceiveProps to UNSAFE_componentWillReceiveProps to suppress this warning in non-strict mode. In React 17.x, only the UNSAFE_ name will work. To rename all deprecated lifecycles to their new names, you can run `npx react-codemod rename-unsafe-lifecycles` in your project source folder.\n\nPlease update the following components: %s"

// componentWillUpdate is deliberately absent from the helper's table: nothing
// in the tree warns about it today, so if something starts, that is news.
const CWU =
  "Warning: componentWillUpdate has been renamed, and is not recommended for use. See https://fb.me/react-unsafe-component-lifecycles for details.\n\n* Move data fetching code or side effects to componentDidUpdate.\n* Rename componentWillUpdate to UNSAFE_componentWillUpdate to suppress this warning in non-strict mode. In React 17.x, only the UNSAFE_ name will work. To rename all deprecated lifecycles to their new names, you can run `npx react-codemod rename-unsafe-lifecycles` in your project source folder.\n\nPlease update the following components: %s"

const EXPECTED_TABLE = [
  {
    lifecycle:  "componentWillMount",
    components: ["VictoryChart", "VictoryStack"]
  },
  {
    lifecycle:  "componentWillReceiveProps",
    components: ["VictoryAxis", "VictoryBar", "VictoryChart", "VictoryStack"]
  },
  { lifecycle: "componentWillReceiveProps", components: ["LinearProgress"] },
  {
    lifecycle:  "componentWillMount",
    components: ["MemoryRouter", "Route", "Router"]
  },
  { lifecycle: "componentWillReceiveProps", components: ["Route", "Router"] },
  {
    lifecycle:  "componentWillMount",
    components: ["SideEffect(DocumentTitle)"]
  }
]

describe("suppressVendorLifecycleWarnings", () => {
  let passedThrough, originalConsoleWarn, restore

  const swallows = (...args) => {
    console.warn(...args)
    assert.lengthOf(
      passedThrough,
      0,
      `expected to be suppressed, but it reached console.warn: ${args[1]}`
    )
  }

  const passesThrough = (...args) => {
    console.warn(...args)
    assert.deepEqual(passedThrough, [args])
  }

  beforeEach(() => {
    passedThrough = []
    // Stand in for the real console.warn before the helper captures it, so
    // whatever it lets through is recorded here instead of reaching the
    // actual test-run output. global_init.js has already installed this
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

  // The anti-tautology check. Compares the real table against the literal copy
  // above, so no entry can be added, removed, renamed or widened without a
  // test failing -- which is what the six suppression cases below, on their
  // own, cannot detect.
  it("suppresses exactly the vendored warnings recorded in this file", () => {
    assert.deepEqual(
      VENDOR_LIFECYCLE_WARNINGS.map(({ lifecycle, components }) => ({
        lifecycle,
        components
      })),
      EXPECTED_TABLE
    )
  })

  it("documents a dependency and a removing phase for every entry", () => {
    VENDOR_LIFECYCLE_WARNINGS.forEach(entry => {
      assert.isNotEmpty(entry.dependency)
      assert.isNotEmpty(entry.removedBy)
    })
  })

  // One case per known warning, with the component list written out here
  // rather than read from the table.
  describe("suppresses the known vendor warnings", () => {
    it("victory's componentWillMount group", () => {
      swallows(CWM, "VictoryChart, VictoryStack")
    })

    it("victory's componentWillReceiveProps group", () => {
      swallows(CWRP, "VictoryAxis, VictoryBar, VictoryChart, VictoryStack")
    })

    it("rmwc's LinearProgress", () => {
      swallows(CWRP, "LinearProgress")
    })

    it("react-router's componentWillMount group", () => {
      swallows(CWM, "MemoryRouter, Route, Router")
    })

    it("react-router's componentWillReceiveProps group", () => {
      swallows(CWRP, "Route, Router")
    })

    it("react-document-title's SideEffect(DocumentTitle)", () => {
      swallows(CWM, "SideEffect(DocumentTitle)")
    })
  })

  // React groups these per commit flush, so the same components arrive in
  // different combinations depending on mocha's file order and on what each
  // test renders. Every regrouping of known names has to keep matching, or the
  // build reds on test-ordering alone.
  describe("is immune to React's per-flush regrouping", () => {
    it("suppresses a subset of a known group", () => {
      swallows(CWM, "MemoryRouter, Router")
    })

    it("suppresses a single name split out of a known group", () => {
      swallows(CWM, "Route")
    })

    it("suppresses a group merged across two dependencies", () => {
      swallows(CWM, "MemoryRouter, Route, Router, VictoryChart, VictoryStack")
    })
  })

  describe("passes through everything else", () => {
    it("an unrelated console.warn", () => {
      passesThrough("Warning: something actually broke")
    })

    // The self-policing property: an unknown name means a component React was
    // not warning about before now uses a deprecated lifecycle -- possibly one
    // of ours -- so the warning must surface even beside known names.
    it("a known group that has gained an unknown component", () => {
      passesThrough(CWM, "VictoryChart, VictoryStack, VideoPlayer")
    })

    it("an unknown component on its own", () => {
      passesThrough(CWM, "VideoPlayer")
    })

    // Known sets are per-lifecycle. LinearProgress is excused for
    // componentWillReceiveProps only; if it ever warns for componentWillMount
    // that is a change worth seeing.
    it("a name that is known for a different lifecycle", () => {
      passesThrough(CWM, "LinearProgress")
    })

    it("a lifecycle that is not in the table", () => {
      passesThrough(CWU, "VictoryChart, VictoryStack")
    })

    it("a matching message with no component-list argument", () => {
      passesThrough(CWM)
    })

    it("an empty component list", () => {
      passesThrough(CWM, "")
    })

    it("a non-string first argument", () => {
      const error = new Error("boom")
      passesThrough(error, "VictoryChart, VictoryStack")
    })
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
      console.error(CWM, "VictoryChart, VictoryStack")
    } finally {
      console.error = originalConsoleError
    }
    assert.lengthOf(errors, 1)
  })
})
