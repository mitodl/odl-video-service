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
 * Deliberately does NOT touch document.title on unmount. This is the one
 * place it diverges from the package, so the divergence is written down here
 * rather than left to be rediscovered:
 *
 * react-document-title 2.0.3 CLEARED the title when its last instance left.
 * Its reducePropsToState reads `propsList[propsList.length - 1]` and returns
 * undefined for an empty list, and handleStateChangeOnClient then does
 * `title || ''` -- so react-side-effect's componentWillUnmount, which splices
 * the instance out and re-emits, wrote an EMPTY document.title once no title
 * component remained. (It did not restore the previous title either; there
 * was no previous title to restore, because it kept no stack.)
 *
 * Not reproducing that is intentional. OVS reaches every route that mounts no
 * DocumentTitle -- /collections/, /help/, /terms/ -- through a plain <a href>
 * (Drawer.js, Footer.js, FAQ.js), i.e. a full page load whose server-rendered
 * <title> the browser applies anyway, so the clear was invisible there. The
 * one place it was reachable is the back button after CollectionListPage's
 * <Link> into a collection: that unmounts the only DocumentTitle
 * client-side, where the package blanked the tab and this keeps the last
 * title. A stale title beats an empty one, and neither is the list page's own
 * title, so there is nothing here worth restoring bug-for-bug.
 *
 * Mounted-instance precedence is not reproduced either, for the same kind of
 * reason: all eight App.js routes are `exact` and mutually exclusive, so two
 * DocumentTitles never mount together and `propsList[length - 1]` had nothing
 * to disambiguate. If nested titles ever become a thing, that logic comes
 * back with them.
 *
 * DocumentTitle_test.js pins the unmount behaviour.
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
