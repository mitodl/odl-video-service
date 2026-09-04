import React from "react"

/**
 * Indeterminate loading bar.
 *
 * Replaces rmwc's `LinearProgress`. rmwc 1.9.4 peers React ^15 || ^16, so it
 * blocked the React 18 upgrade, and it had exactly one consumer -- this file --
 * which made upgrading it to 14 a rewrite of the whole MDC binding layer for a
 * single progress bar.
 *
 * The markup below is MDC's own linear-progress structure. The
 * `@material/linear-progress` styles are already in the bundle, so this is
 * class-compatible with what rmwc emitted; nothing in SCSS changes.
 */
export default class LoadingIndicator extends React.Component {
  render() {
    return (
      <div className="loading-indicator">
        <label>Loading...</label>
        <div
          className="mdc-linear-progress mdc-linear-progress--indeterminate"
          role="progressbar"
        >
          <div className="mdc-linear-progress__buffering-dots" />
          <div className="mdc-linear-progress__buffer" />
          <div className="mdc-linear-progress__bar mdc-linear-progress__primary-bar">
            <span className="mdc-linear-progress__bar-inner" />
          </div>
          <div className="mdc-linear-progress__bar mdc-linear-progress__secondary-bar">
            <span className="mdc-linear-progress__bar-inner" />
          </div>
        </div>
      </div>
    )
  }
}
