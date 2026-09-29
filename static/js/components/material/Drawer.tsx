import React from "react"
import type { UnknownAction } from "redux"
import type { ThunkDispatch } from "redux-thunk"
import { connect } from "react-redux"
import { MDCTemporaryDrawer } from "@material/drawer/dist/mdc.drawer"

import { actions } from "../../actions"
import { makeCollectionUrl } from "../../lib/urls"
import type { Collection } from "../../types/collectionTypes"
import type { RootState } from "../../types/rootState"
import type { AsyncActionCreator } from "../../types/reduxTypes"

const MAX_VISIBLE_COLLECTIONS = 10

/*
 * @material/drawer 0.33 ships no type declarations, so the instance is typed
 * by the three members this component actually uses of it.
 */
type MDCTemporaryDrawerInstance = {
  open: boolean
  listen: (eventName: string, handler: () => void) => void
  destroy: () => void
}

/*
 * `actions` is declared `Record<string, unknown>` in actions/index.ts, because
 * redux-hammock derives the REST slices at runtime, so each one comes back as
 * `unknown` and has to be narrowed where it is used. The cast is erased at
 * runtime -- the call stays a property access on `actions.collectionsList`,
 * which is what the tests stub.
 */
type CollectionsListActions = {
  get: AsyncActionCreator<unknown>
}

type DrawerProps = {
  open: boolean
  onDrawerClose: () => void
  dispatch: ThunkDispatch<RootState, unknown, UnknownAction>
  needsUpdate: boolean
  collections: Array<Collection>
}

class Drawer extends React.Component<DrawerProps> {
  drawer: MDCTemporaryDrawerInstance | null
  drawerRoot: HTMLElement | null
  collapseItemButton: HTMLElement | null

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
      dispatch((actions.collectionsList as CollectionsListActions).get())
    }
  }

  componentDidUpdate(prevProps: DrawerProps) {
    if (this.drawer) {
      if (prevProps.open !== this.props.open) {
        this.drawer.open = this.props.open
      }
    }
  }

  render() {
    const collections = this.props.collections || []
    return (
      <aside
        className="mdc-drawer mdc-drawer--temporary mdc-typography"
        ref={div => {
          this.drawerRoot = div
        }}
      >
        <nav className="mdc-drawer__drawer">
          <nav id="nav-username" className="mdc-drawer__content mdc-list">
            <a
              id="collapse_item"
              className="mdc-list-item mdc-link"
              href="#"
              ref={node => {
                this.collapseItemButton = node
              }}
            >
              {SETTINGS.email ?
                SETTINGS.email :
                SETTINGS.user ?
                  SETTINGS.user :
                  "Not logged in"}
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

const mapStateToProps = (state: RootState) => {
  const { collectionsList, commonUi } = state
  /*
   * `collectionsList.data` is the raw paginated response the API returns --
   * `{ results: [...] }` -- not the bare array rootState.ts declares it to be.
   * Narrowed here rather than corrected there, since that file is out of scope
   * for this conversion; see the reported type gap.
   */
  const collections = collectionsList.loaded ?
    (collectionsList.data as unknown as { results: Array<Collection> })
      .results :
    []
  const needsUpdate = !collectionsList.processing && !collectionsList.loaded

  return {
    collections,
    needsUpdate,
    commonUi
  }
}

export default connect(mapStateToProps)(Drawer)
