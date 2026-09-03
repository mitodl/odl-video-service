/**
 * Silence React 16's deprecated-lifecycle warnings for VENDORED components
 * only -- components we do not author and cannot fix.
 *
 * React 16.9 warns whenever a class defines componentWillMount,
 * componentWillReceiveProps or componentWillUpdate. The warning is not
 * StrictMode-gated (react-dom's recordUnsafeLifecycleWarnings records the
 * un-prefixed lifecycles unconditionally; only the UNSAFE_ variants check
 * fiber.mode), and React's only opt-out is the private
 * __suppressDeprecationWarning marker that react-lifecycles-compat sets.
 * So for a dependency that still uses these lifecycles there is no fix
 * available short of replacing the dependency.
 *
 * `grep -rn "componentWill" static/js` finds no call sites of our own -- the
 * prep phase removed them all -- so every entry below is third-party.
 *
 * WHY THIS IS NOT AN ALLOWLIST LINE IN js_test.sh
 *
 * A `grep -v` line asserts nothing about what it hides: it would swallow any
 * future deprecated-lifecycle warning, including one of OUR components
 * regressing. This matches the exact, sorted component list React names in
 * each warning. If a component joins or leaves that list -- ours or a
 * dependency's -- the match fails and the warning surfaces and fails the run.
 * That is strictly stronger than allowlisting, and it is why the js_test.sh
 * allowlist cap stays at 5.
 *
 * These entries are debt with owners, not permanent exemptions. Each one
 * should be deleted by the change named against it, and deleting the last one
 * should delete this file.
 */

// React sorts the names it reports (setToSortedString does .sort().join(", ")),
// so each list below is deterministic and can be compared exactly.
export const VENDOR_LIFECYCLE_WARNINGS = [
  // victory 0.27.2. Removed by Task 7 of this PR (victory 0.27 -> 37).
  {
    lifecycle:  "componentWillMount",
    components: "VictoryChart, VictoryStack"
  },
  {
    lifecycle:  "componentWillReceiveProps",
    components: "VictoryAxis, VictoryBar, VictoryChart, VictoryStack"
  },
  // rmwc 1.9.4, via its Base/withFoundation HOC. Removed by R2, which drops
  // rmwc entirely.
  {
    lifecycle:  "componentWillReceiveProps",
    components: "LinearProgress"
  },
  // react-router / react-router-dom 4.3.1. No phase owns this yet; 5.0 moved
  // these components to getDerivedStateFromProps.
  {
    lifecycle:  "componentWillMount",
    components: "MemoryRouter, Route, Router"
  },
  {
    lifecycle:  "componentWillReceiveProps",
    components: "Route, Router"
  },
  // react-document-title 2.0.3, via react-side-effect 1.2.0. No phase owns
  // this yet, and react-side-effect 1.2.0 is unmaintained -- the fix is a
  // different title component, not an upgrade.
  {
    lifecycle:  "componentWillMount",
    components: "SideEffect(DocumentTitle)"
  }
]

// react-dom's printWarning prepends "Warning: " to the format string and
// passes the component list as the sole remaining argument, so a matching
// call is exactly two arguments wide.
const prefixFor = lifecycle =>
  `Warning: ${lifecycle} has been renamed, and is not recommended for use.`

const SUFFIX = "Please update the following components: %s"

export function isKnownVendorLifecycleWarning(args) {
  if (args.length !== 2) {
    return false
  }
  const [format, components] = args
  if (typeof format !== "string" || typeof components !== "string") {
    return false
  }
  if (!format.endsWith(SUFFIX)) {
    return false
  }
  return VENDOR_LIFECYCLE_WARNINGS.some(
    known =>
      format.startsWith(prefixFor(known.lifecycle)) &&
      components === known.components
  )
}

/**
 * Patch console.warn for the whole process and return a restore function.
 *
 * Installed once from global_init.js rather than per test file: React dedupes
 * each deprecation warning once per component class per process, so whichever
 * file mounts a given component first is the only one that can observe the
 * warning. Per-file installation would therefore be order-dependent -- pass
 * or fail depending on mocha's file ordering -- which is the flake mode the
 * frozen allowlist exists to prevent.
 *
 * These warnings arrive on console.warn (react-dom calls
 * printWarning("warn", ...)), and nothing in static/js stubs console.warn.
 * The per-file `sandbox.stub(console, "error")` in suppressVictoryKeyWarning
 * is on a different method and cannot shadow this.
 */
export default function suppressVendorLifecycleWarnings() {
  const originalConsoleWarn = console.warn.bind(console)

  console.warn = (...args) => {
    if (isKnownVendorLifecycleWarning(args)) {
      return
    }
    originalConsoleWarn(...args)
  }

  return () => {
    console.warn = originalConsoleWarn
  }
}
