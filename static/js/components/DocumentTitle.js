// @flow
import React from "react"

/**
 * Sets `document.title` and renders its children unchanged.
 *
 * Replaces the `react-document-title` package, which depends on
 * `react-side-effect` 1.2.0 -- unmaintained, peering React ^0.13 || ^0.14 ||
 * ^15 || ^16, and therefore a React 18 blocker that could not be upgraded out
 * of the way. All it did was set the title.
 *
 * Deliberately does NOT restore the previous title on unmount, matching the
 * package's behaviour: OVS relies on a title persisting until the next page
 * sets its own. Restoring would be a behaviour change disguised as a
 * dependency swap. There is a test pinning that.
 */
export default class DocumentTitle extends React.Component<*, void> {
  props: {
    title: string,
    children?: any
  }

  componentDidMount() {
    document.title = this.props.title
  }

  componentDidUpdate(prevProps: { title: string }) {
    if (prevProps.title !== this.props.title) {
      document.title = this.props.title
    }
  }

  render() {
    return this.props.children
  }
}
