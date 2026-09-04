import fs from "fs"
import path from "path"
import { assert } from "chai"

import suppressVendorLifecycleWarnings, {
  VENDOR_LIFECYCLE_WARNINGS,
  VENDOR_LEGACY_CONTEXT_WARNINGS
} from "./suppressVendorLifecycleWarnings"

/**
 * A filter over console.warn/console.error is only safe if it swallows
 * exactly the messages it claims to, and its justification over a js_test.sh
 * allowlist line is that it asserts which components (or, for family C,
 * which single hardcoded message) it will excuse. So these tests must be able
 * to detect either table drifting -- which an earlier version could not,
 * because it was driven by the exported table and therefore asserted the
 * table against itself. A deliberately wrong entry left all its cases
 * passing.
 *
 * Everything expected is therefore written out LITERALLY below, independent of
 * suppressVendorLifecycleWarnings.js: every format string is copied verbatim
 * from react-dom 18.3.1 (cjs/react-dom.development.js -- line numbers noted
 * beside each), and EXPECTED_TABLE / EXPECTED_CONTEXT_TABLE are hand-maintained
 * copies of the two suppression tables.
 *
 * That duplication is deliberate and it IS the check. Do not DRY it up by
 * importing the tables and deriving the expectations from them -- that is
 * exactly the tautology this file exists to avoid. Any edit to a real table
 * has to be made here too, which is the point: it cannot happen silently.
 *
 * PHASE R3 TASK 4 (Ruling R3-5): this file used to cover one family
 * (deprecated lifecycles, on console.warn). It now covers three -- see
 * suppressVendorLifecycleWarnings.js's header for what each is and why they
 * are split across console.warn (family A) and console.error (families B and
 * C). The CWM/CWRP/CWU literals below were re-copied from react-dom 18.3.1
 * (they were previously copied from 16.14.0): React 18 reworded the body of
 * both messages -- fb.me links became reactjs.org/link, and "In React 17.x"
 * became "In React 18.x" -- but neither the opening clause nor the closing
 * "Please update the following components: %s" changed, so the matcher itself
 * needed no code change (see suppressVendorLifecycleWarnings.js's comment on
 * `prefixFor`/`SUFFIX` for why matching only those two anchors makes that
 * true). This file's job is still to catch the NEXT drift, wherever it lands,
 * which is why the literals are kept current rather than left at 16.14.0's
 * text just because the old text happened to still exercise the matcher.
 *
 * HOW A ROW LEAVES A TABLE
 *
 * Phase R1's victory 0.27 -> 37 bump (mitodl/hq#12641) deleted the two victory
 * rows that used to head EXPECTED_TABLE, together with their two suppression
 * cases, the matching rows in the helper, and ledger.sh's cap (6 -> 4) -- all
 * in one commit. A later row leaves the same way, whichever table it is in.
 *
 * Family A also had to rebase five cases whose *data* happened to be victory
 * component names. That is the non-obvious part, and it is why
 * KNOWN_CWM_GROUP below exists and is guarded by a test rather than a comment;
 * read the block above that constant before deleting any row. Family B has no
 * equivalent constant: unlike family A, it does not batch multiple names into
 * one reported group (see suppressVendorLifecycleWarnings.js for why), so
 * there is no grouping carrier data to protect.
 */

// -----------------------------------------------------------------------------
// FAMILY A -- deprecated lifecycles (console.warn)
// -----------------------------------------------------------------------------

// Copied verbatim from react-dom 18.3.1 (cjs/react-dom.development.js lines
// 12906 and 12912). Includes the "Warning: " prefix that printWarning
// prepends and the trailing %s that takes the component list.
const CWM =
  "Warning: componentWillMount has been renamed, and is not recommended for use. See https://reactjs.org/link/unsafe-component-lifecycles for details.\n\n* Move code with side effects to componentDidMount, and set initial state in the constructor.\n* Rename componentWillMount to UNSAFE_componentWillMount to suppress this warning in non-strict mode. In React 18.x, only the UNSAFE_ name will work. To rename all deprecated lifecycles to their new names, you can run `npx react-codemod rename-unsafe-lifecycles` in your project source folder.\n\nPlease update the following components: %s"

const CWRP =
  "Warning: componentWillReceiveProps has been renamed, and is not recommended for use. See https://reactjs.org/link/unsafe-component-lifecycles for details.\n\n* Move data fetching code or side effects to componentDidUpdate.\n* If you're updating state whenever props change, refactor your code to use memoization techniques or move it to static getDerivedStateFromProps. Learn more at: https://reactjs.org/link/derived-state\n* Rename componentWillReceiveProps to UNSAFE_componentWillReceiveProps to suppress this warning in non-strict mode. In React 18.x, only the UNSAFE_ name will work. To rename all deprecated lifecycles to their new names, you can run `npx react-codemod rename-unsafe-lifecycles` in your project source folder.\n\nPlease update the following components: %s"

// componentWillUpdate is deliberately absent from the helper's table: nothing
// in the tree warns about it today, so if something starts, that is news.
const CWU =
  "Warning: componentWillUpdate has been renamed, and is not recommended for use. See https://reactjs.org/link/unsafe-component-lifecycles for details.\n\n* Move data fetching code or side effects to componentDidUpdate.\n* Rename componentWillUpdate to UNSAFE_componentWillUpdate to suppress this warning in non-strict mode. In React 18.x, only the UNSAFE_ name will work. To rename all deprecated lifecycles to their new names, you can run `npx react-codemod rename-unsafe-lifecycles` in your project source folder.\n\nPlease update the following components: %s"

const EXPECTED_TABLE = [
  {
    lifecycle:  "componentWillMount",
    components: ["MemoryRouter", "Route", "Router"]
  },
  { lifecycle: "componentWillReceiveProps", components: ["Route", "Router"] }
]

/**
 * A component list that the table DOES know for componentWillMount, used as
 * the carrier data for cases whose subject is something else entirely.
 *
 * Four cases below assert that a message passes through for a stated reason --
 * an unknown name in the group, a lifecycle absent from the table, a
 * non-string format argument, or being on console.error rather than
 * console.warn. Each is only a real test if the *rest* of the message would
 * otherwise have been suppressed. Feed them names the table does not know and
 * they still pass, but for the wrong reason, testing nothing. That is exactly
 * how they were left when these cases were first written against victory
 * names and victory was then removed from the table.
 *
 * So this group must stay in the table for componentWillMount. It belongs to
 * the react-router row, whose `removedBy` reads "no phase yet" -- meaning
 * whoever removes react-router will be someone with no reason to know any of
 * this. Hence the guard tests in "the carrier data these cases depend on"
 * below: delete that row without touching this constant and they fail loudly,
 * naming the fix. The fix is to REBASE this constant onto whatever
 * componentWillMount names still remain in the table -- never to delete these
 * cases, and never to relax the guard.
 *
 * Named, still-literal constants rather than a value derived from the imported
 * table: deriving it would restore the tautology this whole file exists to
 * avoid, and CWM/CWRP/CWU above set the same precedent.
 */
const KNOWN_CWM_GROUP = "MemoryRouter, Route, Router"

// CROSS_DEPENDENCY_CWM_GROUP removed here, Phase R2, mitodl/hq#12642: it
// proved that a per-commit flush merging componentWillMount names across two
// *different* dependencies still matches, which requires two coexisting
// componentWillMount rows. react-router's and react-document-title's were the
// only two; react-document-title's row is gone (replaced by
// static/js/components/DocumentTitle.js), so the table holds only one
// componentWillMount dependency and the case is no longer expressible. Its
// test case ("suppresses a group merged across two dependencies") and guard
// ("CROSS_DEPENDENCY_CWM_GROUP still spans two dependencies") were removed
// with it. Restore all three together if a second componentWillMount
// dependency is ever added back -- do not rewrite this as a single-dependency
// case that keeps the old name; that would pass while asserting nothing.

// -----------------------------------------------------------------------------
// FAMILY B -- legacy context API (console.error)
// -----------------------------------------------------------------------------

// Copied verbatim from react-dom 18.3.1 (cjs/react-dom.development.js lines
// 18058 and 18066: checkClassInstance), including the "Warning: " prefix and
// the trailing %s printWarning appends for the component stack, which is
// always present here because this check runs during render, not at a
// commit-time flush the way family A does (see suppressVendorLifecycleWarnings.js).
const CHILD_CONTEXT_TYPES =
  "Warning: %s uses the legacy childContextTypes API which is no longer supported and will be removed in the next major release. Use React.createContext() instead\n\n.Learn more about this warning here: https://reactjs.org/link/legacy-context%s"

const CONTEXT_TYPES =
  "Warning: %s uses the legacy contextTypes API which is no longer supported and will be removed in the next major release. Use React.createContext() with static contextType instead.\n\nLearn more about this warning here: https://reactjs.org/link/legacy-context%s"

const EXPECTED_CONTEXT_TABLE = [
  { api: "childContextTypes", components: ["Router", "Route"] },
  { api: "contextTypes", components: ["Link"] }
]

// Family B's matcher checks only that the third argument IS a string (the
// component stack) -- not its content -- so any non-empty string exercises
// the real three-argument shape. See suppressVendorLifecycleWarnings.js.
const STACK = "\n    at Route (test)"

// -----------------------------------------------------------------------------
// FAMILY C -- findDOMNode (console.error)
// -----------------------------------------------------------------------------

// Copied verbatim from react-dom 18.3.1 (cjs/react-dom.development.js line
// 29666: findDOMNode). Unlike families A and B this message has no %s of its
// own -- FIND_DOM_NODE_BASE is exactly what react-dom passes to `error(...)`,
// and printWarning appends the "%s" for the stack itself, which is why
// FIND_DOM_NODE (used in the real, two-argument shape) has one appended below
// and FIND_DOM_NODE_BASE (used for the "no stack argument" pass-through case)
// does not.
const FIND_DOM_NODE_BASE =
  "Warning: findDOMNode is deprecated and will be removed in the next major release. Instead, add a ref directly to the element you want to reference. Learn more about using refs safely here: https://reactjs.org/link/strict-mode-find-node"

const FIND_DOM_NODE = `${FIND_DOM_NODE_BASE}%s`

describe("suppressVendorLifecycleWarnings", () => {
  let passedThroughWarn,
    passedThroughError,
    originalConsoleWarn,
    originalConsoleError,
    restore

  const warnSwallows = (...args) => {
    console.warn(...args)
    assert.lengthOf(
      passedThroughWarn,
      0,
      `expected to be suppressed, but it reached console.warn: ${args[1]}`
    )
  }

  const warnPassesThrough = (...args) => {
    console.warn(...args)
    assert.deepEqual(passedThroughWarn, [args])
  }

  const errorSwallows = (...args) => {
    console.error(...args)
    assert.lengthOf(
      passedThroughError,
      0,
      `expected to be suppressed, but it reached console.error: ${JSON.stringify(
        args
      )}`
    )
  }

  const errorPassesThrough = (...args) => {
    console.error(...args)
    assert.deepEqual(passedThroughError, [args])
  }

  beforeEach(() => {
    passedThroughWarn = []
    passedThroughError = []
    // Stand in for the real console.warn/console.error before the helper
    // captures them, so whatever it lets through is recorded here instead of
    // reaching the actual test-run output. global_init.js has already
    // installed this helper once for the process; installing a second copy
    // over the top is harmless and is what makes this file self-contained.
    originalConsoleWarn = console.warn
    originalConsoleError = console.error
    console.warn = (...args) => {
      passedThroughWarn.push(args)
    }
    console.error = (...args) => {
      passedThroughError.push(args)
    }
    restore = suppressVendorLifecycleWarnings()
  })

  afterEach(() => {
    restore()
    console.warn = originalConsoleWarn
    console.error = originalConsoleError
  })

  describe("family A: deprecated lifecycles (console.warn)", () => {
    // The anti-tautology check. Compares the real table against the literal
    // copy above, so no entry can be added, removed, renamed or widened
    // without a test failing -- which is what the three suppression cases
    // below, on their own, cannot detect.
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

    // The vacuity guard. The cases further down that assert a message PASSES
    // THROUGH only test their stated reason while their carrier names are
    // ones the table would otherwise excuse; if those names stop being known,
    // the cases keep passing and start testing nothing. The deepEqual check
    // above does not catch that -- it guards the table, not the data these
    // cases feed it. This one does, and it fails with instructions rather
    // than a puzzle.
    //
    // Deliberately the only place in this describe block that reads the
    // imported table to decide something. It is not the tautology the header
    // warns about: it asserts a relationship BETWEEN the table and this
    // file's test data, which is precisely the coupling that has silently
    // broken once already.
    describe("the carrier data these cases depend on", () => {
      const namesKnownFor = lifecycle =>
        new Set(
          VENDOR_LIFECYCLE_WARNINGS.filter(
            entry => entry.lifecycle === lifecycle
          ).flatMap(entry => entry.components)
        )

      it("KNOWN_CWM_GROUP is still known for componentWillMount", () => {
        const known = namesKnownFor("componentWillMount")
        const unknown = KNOWN_CWM_GROUP.split(", ").filter(
          name => !known.has(name)
        )
        assert.deepEqual(
          unknown,
          [],
          `KNOWN_CWM_GROUP names ${unknown.join(", ")}, which the table no ` +
            "longer excuses for componentWillMount. A row was removed " +
            "without rebasing this constant. REBASE KNOWN_CWM_GROUP onto " +
            "component names from a surviving componentWillMount row -- do " +
            "not delete the pass-through cases that use it, and do not " +
            "delete this guard: without known carrier names those cases " +
            "pass while asserting nothing. See the comment on " +
            "KNOWN_CWM_GROUP."
        )
      })
    })

    // One case per known warning, with the component list written out here
    // rather than read from the table.
    describe("suppresses the known vendor warnings", () => {
      it("react-router's componentWillMount group", () => {
        warnSwallows(CWM, "MemoryRouter, Route, Router")
      })

      it("react-router's componentWillReceiveProps group", () => {
        warnSwallows(CWRP, "Route, Router")
      })

      // react-document-title's SideEffect(DocumentTitle) case removed here,
      // Phase R2, mitodl/hq#12642: its row is gone from the table, so
      // SideEffect(DocumentTitle) is no longer a known name and this warning
      // would no longer be suppressed.
    })

    // React groups these per commit flush, so the same components arrive in
    // different combinations depending on mocha's file order and on what each
    // test renders. Every regrouping of known names has to keep matching, or
    // the build reds on test-ordering alone.
    describe("is immune to React's per-flush regrouping", () => {
      it("suppresses a subset of a known group", () => {
        warnSwallows(CWM, "MemoryRouter, Router")
      })

      it("suppresses a single name split out of a known group", () => {
        warnSwallows(CWM, "Route")
      })

      // "suppresses a group merged across two dependencies" removed here,
      // Phase R2, mitodl/hq#12642, along with CROSS_DEPENDENCY_CWM_GROUP --
      // see the comment where that constant stood, above.
    })

    describe("passes through everything else", () => {
      it("an unrelated console.warn", () => {
        warnPassesThrough("Warning: something actually broke")
      })

      // The self-policing property: an unknown name means a component React
      // was not warning about before now uses a deprecated lifecycle --
      // possibly one of ours -- so the warning must surface even beside known
      // names.
      it("a known group that has gained an unknown component", () => {
        warnPassesThrough(CWM, `${KNOWN_CWM_GROUP}, VideoPlayer`)
      })

      it("an unknown component on its own", () => {
        warnPassesThrough(CWM, "VideoPlayer")
      })

      it("a lifecycle that is not in the table", () => {
        warnPassesThrough(CWU, KNOWN_CWM_GROUP)
      })

      it("a matching message with no component-list argument", () => {
        warnPassesThrough(CWM)
      })

      it("an empty component list", () => {
        warnPassesThrough(CWM, "")
      })

      it("a non-string first argument", () => {
        const error = new Error("boom")
        warnPassesThrough(error, KNOWN_CWM_GROUP)
      })
    })
  })

  describe("family B: legacy context API (console.error)", () => {
    it("suppresses exactly the vendored warnings recorded in this file", () => {
      assert.deepEqual(
        VENDOR_LEGACY_CONTEXT_WARNINGS.map(({ api, components }) => ({
          api,
          components
        })),
        EXPECTED_CONTEXT_TABLE
      )
    })

    it("documents a dependency and a removing phase for every entry", () => {
      VENDOR_LEGACY_CONTEXT_WARNINGS.forEach(entry => {
        assert.isNotEmpty(entry.dependency)
        assert.isNotEmpty(entry.removedBy)
      })
    })

    describe("suppresses the known vendor warnings", () => {
      it("react-router's Router via childContextTypes", () => {
        errorSwallows(CHILD_CONTEXT_TYPES, "Router", STACK)
      })

      it("react-router's Route via childContextTypes", () => {
        errorSwallows(CHILD_CONTEXT_TYPES, "Route", STACK)
      })

      it("react-router-dom's Link via contextTypes", () => {
        errorSwallows(CONTEXT_TYPES, "Link", STACK)
      })
    })

    describe("passes through everything else", () => {
      it("an unrelated console.error", () => {
        errorPassesThrough("Error: something actually broke")
      })

      // The self-policing property, family B's version: an unknown name
      // means a component of ours (or an unaccounted-for vendor one) is using
      // the legacy context API.
      it("an unknown component name", () => {
        errorPassesThrough(CHILD_CONTEXT_TYPES, "VideoPlayer", STACK)
      })

      // Router is known for childContextTypes, not for contextTypes -- the
      // match is per-api, not just per-name, so this must not pass by
      // accident.
      it("a known name reported under the wrong api", () => {
        errorPassesThrough(CONTEXT_TYPES, "Router", STACK)
      })

      it("a matching message with no stack argument", () => {
        errorPassesThrough(CHILD_CONTEXT_TYPES, "Router")
      })

      it("a non-string stack argument", () => {
        errorPassesThrough(CHILD_CONTEXT_TYPES, "Router", new Error("boom"))
      })

      it("a non-string component-name argument", () => {
        errorPassesThrough(CHILD_CONTEXT_TYPES, 42, STACK)
      })
    })
  })

  describe("family C: findDOMNode (console.error)", () => {
    // No table for this family -- see suppressVendorLifecycleWarnings.js's
    // "FAMILY C'S SAFETY IS DIFFERENT". Its safety comes from ledger.sh's
    // "own findDOMNode call sites" check, not from anything tested here.
    it("suppresses the known vendor warning", () => {
      errorSwallows(FIND_DOM_NODE, STACK)
    })

    describe("passes through everything else", () => {
      it("an unrelated console.error", () => {
        errorPassesThrough("Error: something actually broke")
      })

      it("a matching message with no stack argument", () => {
        errorPassesThrough(FIND_DOM_NODE_BASE)
      })

      it("a non-string stack argument", () => {
        errorPassesThrough(FIND_DOM_NODE, new Error("boom"))
      })

      it("a non-string format argument", () => {
        errorPassesThrough(new Error("boom"), STACK)
      })
    })
  })

  // Family A is on console.warn; families B and C are on console.error. That
  // split is not a stylistic choice -- it is which method react-dom itself
  // calls -- and it must stay a real split: a message shaped like one family
  // must not be excused just because it arrived on the OTHER family's method.
  describe("families do not cross-suppress on the other method", () => {
    it("a family A message on console.error is not suppressed", () => {
      errorPassesThrough(CWM, "MemoryRouter, Route, Router")
    })

    it("a family B message on console.warn is not suppressed", () => {
      warnPassesThrough(CHILD_CONTEXT_TYPES, "Router", STACK)
    })

    it("a family C message on console.warn is not suppressed", () => {
      warnPassesThrough(FIND_DOM_NODE, STACK)
    })
  })
})

/**
 * THE NAME-COLLISION GUARD
 *
 * The family A and family B matchers are by component NAME, and React
 * identifies a component by its class name (type.displayName || type.name).
 * So a component of OURS whose class name equals a vendored name in either
 * table is indistinguishable from the vendored one, and a deprecated
 * lifecycle or legacy-context declaration added to ours would be silently
 * swallowed -- destroying the single property that justifies those two
 * mechanisms over a js_test.sh allowlist line: "an unknown name anywhere in
 * the reported group fails the match ... including one of OUR components
 * regressing". (Family C has no name to collide on; its own safety is the
 * ledger's zero-uses guard, not this one.)
 *
 * That was not hypothetical. static/js/Router.js used to export
 * `class Router`, and "Router" is a known name for family A (both
 * lifecycles) AND family B (childContextTypes) via react-router 4.3.1.
 * Proved by probe: a component of ours named `Router` with a
 * componentWillMount was swallowed (suite exit 0, zero warnings printed); the
 * identical probe named `OvsProbeWidget` reddened the run. Our class is now
 * `AppRouter`, so the table has no collision today.
 *
 * A comment at the react-router row could not have stopped the NEXT collision,
 * so this is a mechanism rather than a comment: it enumerates our own
 * component names out of the source tree and fails if any of them appears in
 * EITHER table, whichever side introduced the clash. Like the carrier-data
 * guard above -- and unlike the tautology this file's header warns about --
 * it cross-checks the tables against an independently maintained second
 * source, here static/js itself.
 */
describe("our own component names vs the vendor suppression tables", () => {
  const SOURCE_ROOT = path.resolve(__dirname, "..")

  // `class X extends React.Component` / `extends Component` /
  // `extends React.PureComponent`, plus a literal `displayName = "X"`, which
  // React prefers over the class name when set. A displayName assembled from
  // a template literal (components/dialogs/hoc.js) is not statically
  // scannable; it is also incapable of equalling a bare vendored name.
  const OWN_NAME_PATTERNS = [
    /\bclass\s+([A-Za-z_$][\w$]*)\s+extends\s+(?:[\w$]+\.)?(?:Pure)?Component\b/g,
    /\bdisplayName\s*[:=]\s*"([^"]+)"/g
  ]

  const jsFilesUnder = dir => {
    return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        return jsFilesUnder(full)
      }
      return entry.isFile() && full.endsWith(".js") ? [full] : []
    })
  }

  // name -> the first file it was declared in, for the failure message.
  const ownComponents = () => {
    const found = new Map()
    jsFilesUnder(SOURCE_ROOT).forEach(file => {
      const source = fs.readFileSync(file, "utf8")
      OWN_NAME_PATTERNS.forEach(pattern => {
        for (const match of source.matchAll(pattern)) {
          if (!found.has(match[1])) {
            found.set(match[1], path.relative(SOURCE_ROOT, file))
          }
        }
      })
    })
    return found
  }

  /**
   * Collisions we have deliberately decided to live with. Empty, and it
   * should stay that way: the fix for a collision is to rename OUR
   * component, which costs one import site. An entry here is a promise that
   * the named component of ours will never grow a deprecated lifecycle or a
   * legacy-context declaration -- which nothing can check -- so it needs a
   * written justification beside it. The stale-entry guard below makes an
   * exemption die with the row it excuses.
   */
  const ACCEPTED_NAME_COLLISIONS = []

  // Union across BOTH tables: a name only needs to appear in one of them to
  // be a live collision risk.
  const tableNames = new Set([
    ...VENDOR_LIFECYCLE_WARNINGS.flatMap(entry => entry.components),
    ...VENDOR_LEGACY_CONTEXT_WARNINGS.flatMap(entry => entry.components)
  ])

  // Anti-vacuity: if the walk or either pattern breaks, every assertion below
  // passes while scanning nothing. These floors are what makes the guard real.
  it("actually finds our own component names", () => {
    const found = ownComponents()
    assert.isAtLeast(
      found.size,
      40,
      `only found ${found.size} component names under static/js -- the walk ` +
        "or OWN_NAME_PATTERNS is broken, and the collision guard below is " +
        "passing vacuously"
    )
    ;["AppRouter", "VideoPlayer", "VideoDetailPage", "ToastMessage"].forEach(
      name => {
        assert.isTrue(
          found.has(name),
          `expected to find our ${name} component; the scanner missed it, so ` +
            "the collision guard below cannot be trusted"
        )
      }
    )
  })

  it("has no component of ours named after a suppressed vendor component", () => {
    const collisions = [...ownComponents()]
      .filter(([name]) => tableNames.has(name))
      .filter(([name]) => !ACCEPTED_NAME_COLLISIONS.includes(name))
      .map(([name, file]) => `${name} (static/js/${file})`)
    assert.deepEqual(
      collisions,
      [],
      `these components of ours share a name with a row in ` +
        `VENDOR_LIFECYCLE_WARNINGS or VENDOR_LEGACY_CONTEXT_WARNINGS: ` +
        `${collisions.join(
          "; "
        )}. React reports components by name, so a deprecated lifecycle or ` +
        "legacy-context declaration added to ours would be SILENTLY " +
        "SUPPRESSED rather than failing the run. Rename OUR component " +
        "(that is what static/js/Router.js's `Router` -> `AppRouter` was " +
        "for); only if that is truly impossible, add the name to " +
        "ACCEPTED_NAME_COLLISIONS above WITH a justification."
    )
  })

  it("carries no stale accepted collision", () => {
    const names = new Set(ownComponents().keys())
    const stale = ACCEPTED_NAME_COLLISIONS.filter(
      name => !(names.has(name) && tableNames.has(name))
    )
    assert.deepEqual(
      stale,
      [],
      `ACCEPTED_NAME_COLLISIONS lists ${stale.join(", ")}, which is no ` +
        "longer both a component of ours and a name in either table. The " +
        "collision is gone, so delete the exemption -- an exemption that " +
        "outlives its collision silently excuses the next one."
    )
  })
})
