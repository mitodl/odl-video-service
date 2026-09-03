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
 * `grep -rnE "componentWill(Mount|ReceiveProps|Update)\b" static/js` finds no
 * call sites of our own -- the prep phase removed them all -- so every name
 * below is third-party. (The looser `grep -rn "componentWill"` returns ~15
 * hits, all componentWillUnmount, which is not deprecated.)
 *
 * The match is by component NAME, and React identifies a component by its
 * class name, so a component of OURS sharing a name with one below would be
 * excused by it -- which is the one way this mechanism can lose its
 * self-policing property. `suppressVendorLifecycleWarnings_test.js` enforces
 * the absence of such a collision with a test, not a comment: see "THE
 * NAME-COLLISION GUARD" there. `static/js/Router.js` exports `AppRouter`
 * rather than `Router` because of it.
 *
 * WHY THIS IS NOT AN ALLOWLIST LINE IN js_test.sh
 *
 * A `grep -v` line asserts nothing about what it hides: it would swallow any
 * future deprecated-lifecycle warning, including one of OUR components
 * regressing. This checks every component name React reports against a known
 * set of vendored names, per lifecycle. An unknown name anywhere in the
 * reported group fails the match, and the warning surfaces and fails the run.
 * That is strictly stronger than allowlisting, and it is why the js_test.sh
 * allowlist cap stays at 5. ledger.sh caps the number of entries here for the
 * same reason it caps that allowlist.
 *
 * WHY SET MEMBERSHIP AND NOT THE WHOLE REPORTED STRING
 *
 * React does not report one warning per component. It accumulates pending
 * fibers and flushes them **per commit**
 * (ReactStrictModeWarnings.flushPendingUnsafeLifecycleWarnings), sorting each
 * group's names and joining them with ", ", after which
 * didWarnAboutUnsafeLifecycles dedupes each class for the rest of the
 * process. So which components share a reported group is a function of which
 * of them happen to mount in the same commit -- which is a function of mocha's
 * file ordering and of what each test renders. Sorting makes the order within
 * a group deterministic; it does not make the grouping deterministic.
 *
 * An earlier version of this file compared the whole reported string for
 * equality, and was therefore fragile against re-partitioning: adding a test
 * file that mounted a bare <MemoryRouter> split "MemoryRouter, Route, Router"
 * into four groups, none of which matched, reddening the build with every test
 * passing and no hint that the remedy was a table edit. Matching membership
 * instead is immune to any regrouping -- subsets, splits, and groups merged
 * across two dependencies all still match -- while losing none of the
 * self-policing property, since an unrecognised name still fails.
 *
 * These entries are debt with owners, not permanent exemptions. Each should be
 * deleted by the change named against it, and deleting the last should delete
 * this file.
 *
 * HOW TO REMOVE A ROW
 *
 * Phase R1's victory 0.27 -> 37 bump (mitodl/hq#12641) removed the two victory
 * rows that used to head this table: Victory 37 uses no deprecated lifecycle,
 * so nothing was left to excuse. That is the pattern -- in one commit, a row
 * leaves here, ledger.sh's "vendor lifecycle suppressions" cap comes down by
 * the same amount, and the literal copy in
 * suppressVendorLifecycleWarnings_test.js loses the matching row.
 *
 * There is a fourth step that is easy to miss, and the tests will not all
 * force it: some cases in that test file use component names from these rows
 * as CARRIER DATA for assertions about something else. Removing a row can
 * leave those cases passing while testing nothing. The affected constants are
 * flagged at the rows below and guarded by tests in that file that fail with
 * instructions. Read those before deleting a row.
 */

export const VENDOR_LIFECYCLE_WARNINGS = [
  // CARRIER DATA (see "HOW TO REMOVE A ROW" above): these three names are
  // KNOWN_CWM_GROUP in suppressVendorLifecycleWarnings_test.js, where four
  // pass-through cases use them as the part of the message that WOULD be
  // suppressed, so that the reason each case names is the only reason it
  // passes through. Remove this row and rebase that constant onto another
  // surviving componentWillMount row; its guard test will fail and tell you
  // so. Two "per-flush regrouping" cases also use these names directly and
  // fail loudly on their own.
  {
    dependency: "react-router / react-router-dom 4.3.1",
    removedBy:  "no phase yet; 5.0 moved these to getDerivedStateFromProps",
    lifecycle:  "componentWillMount",
    components: ["MemoryRouter", "Route", "Router"]
  },
  {
    dependency: "react-router / react-router-dom 4.3.1",
    removedBy:  "no phase yet; 5.0 moved these to getDerivedStateFromProps",
    lifecycle:  "componentWillReceiveProps",
    components: ["Route", "Router"]
  },
  // CARRIER DATA: the second half of CROSS_DEPENDENCY_CWM_GROUP in the test
  // file. That case proves a flush merging names across dependencies still
  // matches, so it needs this row and the react-router componentWillMount row
  // above to coexist. Remove either and the case becomes inexpressible; its
  // guard test fails and says what to do.
  {
    dependency: "react-document-title 2.0.3, via react-side-effect 1.2.0",
    removedBy:
      "no phase yet; react-side-effect 1.2.0 is unmaintained, so this needs a different title component rather than an upgrade",
    lifecycle:  "componentWillMount",
    components: ["SideEffect(DocumentTitle)"]
  }
]

// react-dom's printWarning prepends "Warning: " to the format string and
// passes the joined component list as the sole remaining argument, so a
// matching call is exactly two arguments wide. If React ever appended a
// component stack as well the call would be three wide and the warning would
// surface rather than hide -- fail-safe, which is the right direction.
const prefixFor = lifecycle =>
  `Warning: ${lifecycle} has been renamed, and is not recommended for use.`

const SUFFIX = "Please update the following components: %s"

// Union of the known names for one lifecycle, across every dependency. The
// union rather than one row at a time, because a single flush can group
// components from two different dependencies together.
const knownNamesFor = lifecycle =>
  new Set(
    VENDOR_LIFECYCLE_WARNINGS.filter(
      entry => entry.lifecycle === lifecycle
    ).flatMap(entry => entry.components)
  )

const KNOWN_LIFECYCLES = [
  ...new Set(VENDOR_LIFECYCLE_WARNINGS.map(entry => entry.lifecycle))
]

export function isKnownVendorLifecycleWarning(args) {
  if (args.length !== 2) {
    return false
  }
  const [format, reported] = args
  if (typeof format !== "string" || typeof reported !== "string") {
    return false
  }
  if (!format.endsWith(SUFFIX)) {
    return false
  }
  const lifecycle = KNOWN_LIFECYCLES.find(candidate =>
    format.startsWith(prefixFor(candidate))
  )
  if (!lifecycle) {
    return false
  }
  const known = knownNamesFor(lifecycle)
  // An empty reported list splits to [""], which is not a known name, so it
  // fails the match rather than matching vacuously.
  return reported.split(", ").every(name => known.has(name))
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
 * printWarning("warn", ...)), and nothing else in static/js touches
 * console.warn. Any per-file `sandbox.stub(console, "error")` elsewhere in the
 * suite is on a different method and cannot shadow this.
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
