import fs from "fs"
import path from "path"
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
 * HOW A ROW LEAVES THIS TABLE
 *
 * Phase R1's victory 0.27 -> 37 bump (mitodl/hq#12641) deleted the two victory
 * rows that used to head EXPECTED_TABLE, together with their two suppression
 * cases, the matching rows in the helper, and ledger.sh's cap (6 -> 4) -- all
 * in one commit. A later row leaves the same way.
 *
 * It also had to rebase five cases whose *data* happened to be victory
 * component names. That is the non-obvious part, and it is why
 * KNOWN_CWM_GROUP below exists and is guarded by a test rather than a comment;
 * read the block above that constant before deleting any row.
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
    components: ["MemoryRouter", "Route", "Router"]
  },
  { lifecycle: "componentWillReceiveProps", components: ["Route", "Router"] },
  {
    lifecycle:  "componentWillMount",
    components: ["SideEffect(DocumentTitle)"]
  }
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

/**
 * A componentWillMount group spanning TWO table rows from two different
 * dependencies (react-router and react-document-title). Its case exists to
 * prove that React's per-commit flush merging names across dependencies still
 * matches, so it needs at least two rows to share one lifecycle. If either
 * contributing row leaves, its guard below fails and says so; the case itself
 * would also fail, so unlike the four above this one is self-announcing.
 */
const CROSS_DEPENDENCY_CWM_GROUP = `${KNOWN_CWM_GROUP}, SideEffect(DocumentTitle)`

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
  // test failing -- which is what the three suppression cases below, on their
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

  // The vacuity guard. The cases further down that assert a message PASSES
  // THROUGH only test their stated reason while their carrier names are ones
  // the table would otherwise excuse; if those names stop being known, the
  // cases keep passing and start testing nothing. The deepEqual check above
  // does not catch that -- it guards the table, not the data these cases feed
  // it. These two do, and they fail with instructions rather than a puzzle.
  //
  // Deliberately the only place in this file that reads the imported table to
  // decide something. It is not the tautology the header warns about: it
  // asserts a relationship BETWEEN the table and this file's test data, which
  // is precisely the coupling that has silently broken once already.
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
          "longer excuses for componentWillMount. A row was removed without " +
          "rebasing this constant. REBASE KNOWN_CWM_GROUP onto component " +
          "names from a surviving componentWillMount row -- do not delete " +
          "the pass-through cases that use it, and do not delete this guard: " +
          "without known carrier names those cases pass while asserting " +
          "nothing. See the comment on KNOWN_CWM_GROUP."
      )
    })

    it("CROSS_DEPENDENCY_CWM_GROUP still spans two dependencies", () => {
      const names = new Set(CROSS_DEPENDENCY_CWM_GROUP.split(", "))
      const dependencies = new Set(
        VENDOR_LIFECYCLE_WARNINGS.filter(
          entry =>
            entry.lifecycle === "componentWillMount" &&
            entry.components.some(name => names.has(name))
        ).map(entry => entry.dependency)
      )
      assert.isAtLeast(
        dependencies.size,
        2,
        "CROSS_DEPENDENCY_CWM_GROUP no longer draws componentWillMount names " +
          `from two different dependencies (found ${dependencies.size}). ` +
          "Rebuild it from two surviving componentWillMount rows belonging " +
          "to different dependencies; if only one such row is left, the " +
          "'merged across two dependencies' case is no longer expressible " +
          "and should be deleted along with this guard and the constant."
      )
    })
  })

  // One case per known warning, with the component list written out here
  // rather than read from the table.
  describe("suppresses the known vendor warnings", () => {
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
      swallows(CWM, CROSS_DEPENDENCY_CWM_GROUP)
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
      passesThrough(CWM, `${KNOWN_CWM_GROUP}, VideoPlayer`)
    })

    it("an unknown component on its own", () => {
      passesThrough(CWM, "VideoPlayer")
    })

    it("a lifecycle that is not in the table", () => {
      passesThrough(CWU, KNOWN_CWM_GROUP)
    })

    it("a matching message with no component-list argument", () => {
      passesThrough(CWM)
    })

    it("an empty component list", () => {
      passesThrough(CWM, "")
    })

    it("a non-string first argument", () => {
      const error = new Error("boom")
      passesThrough(error, KNOWN_CWM_GROUP)
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
      console.error(CWM, KNOWN_CWM_GROUP)
    } finally {
      console.error = originalConsoleError
    }
    assert.lengthOf(errors, 1)
  })
})

/**
 * THE NAME-COLLISION GUARD
 *
 * The matcher is by component NAME, and React identifies a component by its
 * class name (type.displayName || type.name). So a component of OURS whose
 * class name equals a vendored name in the table is indistinguishable from the
 * vendored one, and a deprecated lifecycle added to ours would be silently
 * swallowed -- destroying the single property that justifies this mechanism
 * over a js_test.sh allowlist line: "an unknown name anywhere in the reported
 * group fails the match ... including one of OUR components regressing".
 *
 * That was not hypothetical. static/js/Router.js used to export
 * `class Router`, and "Router" is a known name for BOTH lifecycles via
 * react-router 4.3.1. Proved by probe: a component of ours named `Router` with
 * a componentWillMount was swallowed (suite exit 0, zero warnings printed);
 * the identical probe named `OvsProbeWidget` reddened the run. Our class is
 * now `AppRouter`, so the table has no collision today.
 *
 * A comment at the react-router row could not have stopped the NEXT collision,
 * so this is a mechanism rather than a comment: it enumerates our own
 * component names out of the source tree and fails if any of them appears in
 * the table, whichever side introduced the clash. Like the carrier-data guards
 * above -- and unlike the tautology this file's header warns about -- it
 * cross-checks the table against an independently maintained second source,
 * here static/js itself.
 */
describe("our own component names vs the vendor suppression table", () => {
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
   * Collisions we have deliberately decided to live with. Empty, and it should
   * stay that way: the fix for a collision is to rename OUR component, which
   * costs one import site. An entry here is a promise that the named component
   * of ours will never grow a deprecated lifecycle -- which nothing can check
   * -- so it needs a written justification beside it. The stale-entry guard
   * below makes an exemption die with the row it excuses.
   */
  const ACCEPTED_NAME_COLLISIONS = []

  const tableNames = new Set(
    VENDOR_LIFECYCLE_WARNINGS.flatMap(entry => entry.components)
  )

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
        `VENDOR_LIFECYCLE_WARNINGS: ${collisions.join("; ")}. React reports ` +
        "components by name, so a deprecated lifecycle added to ours would " +
        "be SILENTLY SUPPRESSED rather than failing the run. Rename OUR " +
        "component (that is what static/js/Router.js's `Router` -> " +
        "`AppRouter` was for); only if that is truly impossible, add the " +
        "name to ACCEPTED_NAME_COLLISIONS above WITH a justification."
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
        "longer both a component of ours and a name in the table. The " +
        "collision is gone, so delete the exemption -- an exemption that " +
        "outlives its collision silently excuses the next one."
    )
  })
})
