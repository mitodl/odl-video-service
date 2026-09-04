/**
 * Silence React's ungated deprecation warnings for VENDORED components only --
 * components we do not author and cannot fix. As of Phase R3 Task 4 (Ruling
 * R3-5) this covers THREE families, not one, because React 18 surfaced two
 * more once RTL 16 cleared the noise that had hidden them (see mitodl/hq#12643).
 * All three still trace to dependencies with no owning phase:
 *
 *   FAMILY A -- deprecated lifecycles (componentWillMount,
 *   componentWillReceiveProps). React 16.9+ warns whenever a class defines
 *   these unprefixed. The warning is not StrictMode-gated (react-dom's
 *   flushPendingUnsafeLifecycleWarnings records the un-prefixed lifecycles
 *   unconditionally; only the UNSAFE_ variants check fiber.mode), and React's
 *   only opt-out is the private __suppressDeprecationWarning marker that
 *   react-lifecycles-compat sets. Fires on console.warn.
 *
 *   FAMILY B -- the legacy context API (childContextTypes / contextTypes).
 *   React 18 warns once per component CLASS the first time it mounts, unless
 *   running in StrictMode (which this app does not). Fires on console.error.
 *
 *   FAMILY C -- findDOMNode. React 18 warns the first time findDOMNode is
 *   called anywhere in the process (module-level `didWarnAboutFindDOMNode`
 *   flag in react-dom -- see react-dom/cjs/react-dom.development.js). Fires
 *   on console.error. UNLIKE THE OTHER TWO, THE MESSAGE NAMES NO COMPONENT:
 *   React appends the component stack as a second argument, but there is no
 *   %s for a name to check membership against. See "FAMILY C'S SAFETY IS
 *   DIFFERENT" below.
 *
 * `grep -rnE "componentWill(Mount|ReceiveProps|Update)\b" static/js` finds no
 * call sites of our own for family A -- the prep phase removed them all. For
 * families B and C, Ruling R3-5 verified by grep that static/js uses
 * findDOMNode, childContextTypes, contextTypes and getChildContext ZERO times
 * (excluding this file and its test, which reference the names as STRING DATA
 * -- matcher literals and prose -- not as declarations or call sites).
 * `scripts/test/ledger.sh`'s "own findDOMNode call sites" and "own legacy
 * context API declarations" checks assert this stays true on every run: see
 * "FAMILY C'S SAFETY IS DIFFERENT" below for why that machine-checked
 * precondition, rather than name matching, is what makes suppressing family C
 * defensible.
 *
 * The match for families A and B is by component NAME, and React identifies a
 * component by its class name, so a component of OURS sharing a name with one
 * below would be excused by it -- which is the one way this mechanism can lose
 * its self-policing property for those two families. `suppressVendorLifecycleWarnings_test.js`
 * enforces the absence of such a collision with a test, not a comment: see
 * "THE NAME-COLLISION GUARD" there, which now covers both tables.
 * `static/js/Router.js` exports `AppRouter` rather than `Router` because of it.
 *
 * WHY THIS IS NOT AN ALLOWLIST LINE IN js_test.sh
 *
 * A `grep -v` line asserts nothing about what it hides: it would swallow any
 * future warning of the same shape, including one of OUR components
 * regressing. Families A and B check every component name React reports
 * against a known set of vendored names; an unknown name anywhere in the
 * reported group fails the match, and the warning surfaces and fails the run.
 * That is strictly stronger than allowlisting, and it is why the js_test.sh
 * allowlist cap stays at 5. Family C has no name to check -- its safety comes
 * from the ledger guard instead, which is just as machine-checked, only at a
 * different layer. ledger.sh caps the number of entries here for the same
 * reason it caps that allowlist.
 *
 * WHY SET MEMBERSHIP AND NOT THE WHOLE REPORTED STRING (families A and B)
 *
 * React does not report one deprecated-lifecycle warning per component. It
 * accumulates pending fibers and flushes them **per commit**
 * (ReactStrictModeWarnings.flushPendingUnsafeLifecycleWarnings for family A),
 * sorting each group's names and joining them with ", ", after which
 * didWarnAboutUnsafeLifecycles dedupes each class for the rest of the
 * process. So which components share a reported group is a function of which
 * of them happen to mount in the same commit -- which is a function of mocha's
 * file ordering and of what each test renders. Sorting makes the order within
 * a group deterministic; it does not make the grouping deterministic. Family B
 * warns per-component rather than batching a group (each call carries exactly
 * one name), so it has no grouping to be immune to, but is matched by set
 * membership anyway for the same reason: it stays correct if a row's known
 * names ever grow.
 *
 * An earlier version of the family A matcher compared the whole reported
 * string for equality, and was therefore fragile against re-partitioning:
 * adding a test file that mounted a bare <MemoryRouter> split "MemoryRouter,
 * Route, Router" into four groups, none of which matched, reddening the build
 * with every test passing and no hint that the remedy was a table edit.
 * Matching membership instead is immune to any regrouping -- subsets, splits,
 * and groups merged across two dependencies all still match -- while losing
 * none of the self-policing property, since an unrecognised name still fails.
 *
 * WHY CONSOLE.WARN FOR FAMILY A BUT CONSOLE.ERROR FOR FAMILIES B AND C
 *
 * This is not a design choice made here -- it is which method react-dom calls
 * (`warn(...)` vs `error(...)` in react-dom/cjs/react-dom.development.js).
 * Deprecated-lifecycle warnings call `warn`; legacy-context and findDOMNode
 * warnings call `error`. So the installer below patches BOTH methods, each
 * independently, with its own set of known messages. A per-file
 * `sandbox.stub(console, "error")` (there is exactly one in the suite today,
 * CollectionFormDialog_test.js) temporarily replaces console.error for the
 * duration of that test and its own sandbox.restore() puts back whatever was
 * there before -- which, since this installer runs once at process start
 * (before any test file), is always this file's wrapped console.error. So the
 * shadow is confined to that one test and self-heals; it does not touch
 * console.warn, which family A depends on, at all. (That test does not render
 * anything from families B or C, so nothing is lost in the shadow today.)
 *
 * These entries are debt with owners, not permanent exemptions. Each should be
 * deleted by the change named against it, and deleting the last row of a
 * family (or all three) should delete the corresponding table (or this file).
 *
 * HOW TO REMOVE A ROW
 *
 * Phase R1's victory 0.27 -> 37 bump (mitodl/hq#12641) removed the two victory
 * rows that used to head this table: Victory 37 uses no deprecated lifecycle,
 * so nothing was left to excuse. That is the pattern -- in one commit, a row
 * leaves here, ledger.sh's relevant cap comes down by the same amount, and the
 * literal copy in suppressVendorLifecycleWarnings_test.js loses the matching
 * row.
 *
 * There is a fourth step that is easy to miss, and the tests will not all
 * force it: some cases in that test file use component names from these rows
 * as CARRIER DATA for assertions about something else. Removing a row can
 * leave those cases passing while testing nothing. The affected constants are
 * flagged at the rows below and guarded by tests in that file that fail with
 * instructions. Read those before deleting a row.
 *
 * FAMILY C'S SAFETY IS DIFFERENT
 *
 * findDOMNode's warning names no component at all -- `error('findDOMNode is
 * deprecated ...')` takes no format argument, so there is nothing to check
 * membership against the way families A and B do. React can't tell OUR calls
 * to findDOMNode apart from a vendor's; the warning fires once per PROCESS
 * (react-dom's module-level `didWarnAboutFindDOMNode` flag), not once per
 * component. So suppressing this message is safe only for as long as our own
 * code never calls findDOMNode -- if it ever does, this suppression would
 * swallow that regression exactly as silently as a js_test.sh allowlist line
 * would, with no name check to save it.
 *
 * That precondition is therefore enforced OUTSIDE this file, in
 * scripts/test/ledger.sh's "own findDOMNode call sites" check, which greps all
 * of static/js (excluding this file and its test) for `findDOMNode(` call
 * sites and fails the run the moment one appears. The identical reasoning
 * applies to family B's legacy context API -- its per-name matching already
 * gives it the same self-policing property as family A, but the ledger's "own
 * legacy context API declarations" check is a second, independent guard for
 * it too, at zero extra cost.
 */

// -----------------------------------------------------------------------------
// FAMILY A -- deprecated lifecycles (console.warn)
// -----------------------------------------------------------------------------

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
  }
  // react-document-title 2.0.3 (via react-side-effect 1.2.0) removed here,
  // Phase R2, mitodl/hq#12642: replaced with static/js/components/
  // DocumentTitle.js, so nothing is left to excuse. Its row's
  // componentWillMount entry was the second half of
  // CROSS_DEPENDENCY_CWM_GROUP in the test file, which is now deleted rather
  // than rebased -- see that file for why.
]

// react-dom's printWarning prepends "Warning: " to the format string and
// passes the joined component list as the sole remaining argument, so a
// matching call is exactly two arguments wide. If React ever appended a
// component stack as well the call would be three wide and the warning would
// surface rather than hide -- fail-safe, which is the right direction.
//
// Phase R3 Task 4: React 18 reworded the BODY of both messages (the
// fb.me links became reactjs.org/link, and "In React 17.x" became "In React
// 18.x" -- see suppressVendorLifecycleWarnings_test.js's CWM/CWRP, now
// re-copied from react-dom 18.3.1). Neither the prefix nor the suffix below
// changed, so this matcher -- which checks only those two anchors and ignores
// the body prose between them -- needed NO code change to keep matching under
// React 18. Verified empirically: disabling the installer and mounting a
// router under React 18 reproduces both warnings verbatim from react-dom
// 18.3.1's source, and re-enabling it suppresses them exactly as before.
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

// -----------------------------------------------------------------------------
// FAMILY B -- legacy context API (console.error)
// -----------------------------------------------------------------------------

export const VENDOR_LEGACY_CONTEXT_WARNINGS = [
  {
    dependency: "react-router 4.3.1",
    removedBy:  "no phase yet; react-router 5.0 removed the legacy context API",
    api:        "childContextTypes",
    components: ["Router", "Route"]
  },
  {
    dependency: "react-router-dom 4.3.1",
    removedBy:
      "no phase yet; react-router-dom 5.0 removed the legacy context API",
    api:        "contextTypes",
    components: ["Link"]
  }
]

// react-dom's checkClassInstance warns with the component name as the ONLY
// %s in its own format string, then printWarning appends the component stack
// as a SECOND %s plus a matching third argument -- because this check runs
// during render (mountClassInstance/updateClassInstance), where
// ReactDebugCurrentFrame always has a stack, unlike family A's commit-time
// flush. So a matching call is exactly THREE arguments wide: (format, name,
// stack). That is a real structural difference from family A, not an
// oversight -- verified empirically (see suppressVendorLifecycleWarnings_test.js
// and the Task 4 report) and against react-dom 18.3.1's source
// (react-dom/cjs/react-dom.development.js, checkClassInstance).
const legacyContextPrefixFor = api =>
  `Warning: %s uses the legacy ${api} API which is no longer supported and ` +
  "will be removed in the next major release."

// Both childContextTypes and contextTypes messages end with this exact
// sentence before the appended stack %s. Checking it, in addition to the
// prefix, is the same fail-safe anchor family A uses.
const LEGACY_CONTEXT_SUFFIX =
  "Learn more about this warning here: https://reactjs.org/link/legacy-context"

const knownLegacyContextNamesFor = api =>
  new Set(
    VENDOR_LEGACY_CONTEXT_WARNINGS.filter(entry => entry.api === api).flatMap(
      entry => entry.components
    )
  )

const KNOWN_CONTEXT_APIS = [
  ...new Set(VENDOR_LEGACY_CONTEXT_WARNINGS.map(entry => entry.api))
]

export function isKnownVendorLegacyContextWarning(args) {
  if (args.length !== 3) {
    return false
  }
  const [format, name, stack] = args
  if (
    typeof format !== "string" ||
    typeof name !== "string" ||
    typeof stack !== "string"
  ) {
    return false
  }
  const api = KNOWN_CONTEXT_APIS.find(
    candidate =>
      format.startsWith(legacyContextPrefixFor(candidate)) &&
      // The stack's own %s was appended after this suffix, so check the
      // substring rather than endsWith.
      format.includes(LEGACY_CONTEXT_SUFFIX)
  )
  if (!api) {
    return false
  }
  return knownLegacyContextNamesFor(api).has(name)
}

// -----------------------------------------------------------------------------
// FAMILY C -- findDOMNode (console.error)
// -----------------------------------------------------------------------------
//
// No table, no component names, nothing to match membership against -- see
// "FAMILY C'S SAFETY IS DIFFERENT" above. This is one hardcoded literal,
// copied verbatim from react-dom 18.3.1's source (react-dom/cjs/
// react-dom.development.js, function findDOMNode) and re-verified by
// suppressVendorLifecycleWarnings_test.js's own independent copy. Its safety
// comes from scripts/test/ledger.sh's "own findDOMNode call sites" check, not
// from anything in this file.
const FIND_DOM_NODE_MESSAGE =
  "Warning: findDOMNode is deprecated and will be removed in the next major " +
  "release. Instead, add a ref directly to the element you want to " +
  "reference. Learn more about using refs safely here: " +
  "https://reactjs.org/link/strict-mode-find-node"

export function isKnownVendorFindDOMNodeWarning(args) {
  if (args.length !== 2) {
    return false
  }
  const [format, stack] = args
  // react-dom's `error(...)` call for this warning takes no arguments of its
  // own; printWarning appends the component stack as the sole %s and sole
  // extra argument. So the format is the literal message plus a trailing
  // "%s" for that stack -- exact equality, not startsWith/endsWith, because
  // there is no component-specific text in the middle to allow for.
  return (
    typeof format === "string" &&
    typeof stack === "string" &&
    format === `${FIND_DOM_NODE_MESSAGE}%s`
  )
}

// -----------------------------------------------------------------------------
// Installer
// -----------------------------------------------------------------------------

/**
 * Patch console.warn and console.error for the whole process and return a
 * restore function for both.
 *
 * Installed once from global_init.js rather than per test file: React dedupes
 * each of these warnings once per component class (families A and B) or once
 * per process (family C), so whichever file mounts/calls first is the only
 * one that can observe it. Per-file installation would therefore be
 * order-dependent -- pass or fail depending on mocha's file ordering -- which
 * is the flake mode the frozen allowlist exists to prevent.
 */
export default function suppressVendorLifecycleWarnings() {
  const originalConsoleWarn = console.warn.bind(console)
  const originalConsoleError = console.error.bind(console)

  console.warn = (...args) => {
    if (isKnownVendorLifecycleWarning(args)) {
      return
    }
    originalConsoleWarn(...args)
  }

  console.error = (...args) => {
    if (
      isKnownVendorLegacyContextWarning(args) ||
      isKnownVendorFindDOMNodeWarning(args)
    ) {
      return
    }
    originalConsoleError(...args)
  }

  return () => {
    console.warn = originalConsoleWarn
    console.error = originalConsoleError
  }
}
