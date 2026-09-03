/**
 * Silence Victory 0.27.2's spurious "unique key prop" warning.
 *
 * AnalyticsChart mounts a real Victory chart. VictoryAxis's own
 * tick-rendering code omits a `key` prop on an array of children, which
 * React reports via console.error on every mount. Enzyme's `shallow`
 * rendering never mounted this child, so the defect -- which lives entirely
 * inside Victory, not in our usage of it or in anything these tests assert
 * on -- was never exercised before the RTL conversion. The rendered SVG is
 * unaffected.
 *
 * Only this one known, harmless message is filtered, so it can't fail the
 * test run's console-output check. Every other console.error still comes
 * through and still fails the run.
 *
 * React 16 reworded the message and split it across console.error's format
 * arguments: the first argument carries the "Each child in a list" text with
 * `%s` placeholders, and the owner -- "Check the render method of
 * `VictoryAxis`." -- arrives as a later argument. So the guard has to look at
 * the format string for the defect and at the remaining arguments for the
 * owner. Matching the owner phrase rather than the bare component name keeps
 * this as narrow as it was on React 15: React appends a component stack as
 * the final argument, and that stack names VictoryAxis for *any* warning
 * raised anywhere inside a chart.
 *
 * Call from a `beforeEach` with the sandbox that a matching `afterEach`
 * restores -- there is no separate teardown to remember.
 */
const KEY_WARNING = 'Each child in a list should have a unique "key" prop'
const VICTORY_AXIS_OWNER = "Check the render method of `VictoryAxis`."

export default function suppressVictoryKeyWarning(sandbox) {
  const originalConsoleError = console.error.bind(console)

  return sandbox.stub(console, "error").callsFake((...args) => {
    const [message] = args
    if (
      typeof message === "string" &&
      message.includes(KEY_WARNING) &&
      args.some(
        arg => typeof arg === "string" && arg.includes(VICTORY_AXIS_OWNER)
      )
    ) {
      return
    }
    originalConsoleError(...args)
  })
}
