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
 * Call from a `beforeEach` with the sandbox that a matching `afterEach`
 * restores -- there is no separate teardown to remember.
 */
export default function suppressVictoryKeyWarning(sandbox) {
  const originalConsoleError = console.error.bind(console)

  return sandbox.stub(console, "error").callsFake((...args) => {
    const [message] = args
    if (
      typeof message === "string" &&
      message.includes(
        'Each child in an array or iterator should have a unique "key" prop'
      ) &&
      message.includes("VictoryAxis")
    ) {
      return
    }
    originalConsoleError(...args)
  })
}
