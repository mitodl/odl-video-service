// @flow
/* global SETTINGS: false */
import React from "react"
import type { Dispatch } from "redux"
import { connect } from "react-redux"
import { MDCTemporaryDrawer } from "@material/drawer/dist/mdc.drawer"

import { actions } from "../../actions"
import { makeCollectionUrl } from "../../lib/urls"
import type { Collection } from "../../flow/collectionTypes"

const MAX_VISIBLE_COLLECTIONS = 10

type DrawerProps = {
  open: boolean,
  onDrawerClose: () => void,
  dispatch: Dispatch,
  needsUpdate: boolean,
  collections: Array<Collection>
}

class Drawer extends React.Component<*, void> {
  drawer: null
  drawerRoot: ?HTMLElement
  collapseItemButton: ?HTMLElement
  props: DrawerProps

  componentDidMount() {
    const { onDrawerClose } = this.props
    this.drawer = new MDCTemporaryDrawer(this.drawerRoot)
    this.drawer.listen("MDCTemporaryDrawer:close", onDrawerClose)
    this.updateRequirements()

    // Attach click listeners here; this is a necessary hack to get around MDC limitations
    if (this.collapseItemButton) {
      // make flow happy
      this.collapseItemButton.addEventListener(
        "click",
        (event: MouseEvent) => {
          event.preventDefault()
          onDrawerClose()
        },
        false
      )
    }
  }

  componentWillUnmount() {
    if (this.drawer) {
      this.drawer.destroy()
    }
  }

  updateRequirements = () => {
    const { dispatch, needsUpdate } = this.props
    if (needsUpdate) {
      dispatch(actions.collectionsList.get())
    }
  }

  componentWillReceiveProps(nextProps: DrawerProps) {
    if (this.drawer) {
      if (this.props.open !== nextProps.open) {
        this.drawer.open = nextProps.open
      }
    }
  }

  render() {
    const collections = this.props.collections || []
    return (
      <aside
        className="mdc-drawer mdc-drawer--temporary mdc-typography"
        ref={div => (this.drawerRoot = div)}
      >
        <nav className="mdc-drawer__drawer">
          <nav id="nav-username" className="mdc-drawer__content mdc-list">
            <a
              id="collapse_item"
              className="mdc-list-item mdc-link"
              href="#"
              ref={node => (this.collapseItemButton = node)}
            >
              {SETTINGS.email
                ? SETTINGS.email
                : SETTINGS.user ? SETTINGS.user : "Not logged in"}
            </a>
          </nav>
          <header className="mdc-drawer__header">
            <div className="mdc-drawer__header-content">
              <a href="/collections/" style={{ color: "inherit" }}>
                My Collections
              </a>
            </div>
          </header>
          <nav id="nav-collections" className="mdc-drawer__content mdc-list">
            {collections.slice(0, MAX_VISIBLE_COLLECTIONS).map(col => (
              <a
                className="mdc-list-item mdc-list-item--activated"
                href={makeCollectionUrl(col.key)}
                key={col.key}
              >
                {col.title} ({col.video_count})
              </a>
            ))}
            {collections.length > MAX_VISIBLE_COLLECTIONS ? (
              <a
                className="mdc-list-item mdc-list-item more-collections-button"
                href="/collections/"
              >
                more collections…
              </a>
            ) : null}
          </nav>
          <nav
            id="icon-with-text-demo"
            className="mdc-drawer__content mdc-list"
          >
            <a className="mdc-list-item mdc-link" href="/help/">
              <i
                className="material-icons mdc-list-item__graphic"
                aria-hidden="true"
              >
                help_outline
              </i>
              Help
            </a>
            {SETTINGS.user ? (
              <a className="mdc-list-item mdc-link logout" href="/logout/">
                <i
                  className="material-icons mdc-list-item__graphic"
                  aria-hidden="true"
                >
                  input
                </i>
                Log out
              </a>
            ) : null}
          </nav>
        </nav>
      </aside>
    )
  }
}

const mapStateToProps = state => {
  const { collectionsList, commonUi } = state
  const collections = collectionsList.loaded ? collectionsList.data.results : []
  const needsUpdate = !collectionsList.processing && !collectionsList.loaded

  return {
    collections,
    needsUpdate,
    commonUi
  }
}

export default connect(mapStateToProps)(Drawer)
