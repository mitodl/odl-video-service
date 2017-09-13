// @flow
/* global SETTINGS: false */
import React from 'react';
import type { Dispatch } from "redux";
import { connect } from 'react-redux';
import { MDCTemporaryDrawer } from '@material/drawer/dist/mdc.drawer';

import { actions } from '../../actions';
import * as collectionUiActions from '../../actions/collectionUi';
import { makeCollectionUrl } from "../../lib/urls";
import type { Collection } from "../../flow/collectionTypes";

type DrawerProps = {
  open: boolean,
  onDrawerClose: () => void,
  dispatch: Dispatch,
  needsUpdate: boolean,
  collections: Array<Collection>
};

class Drawer extends React.Component {
  drawer: null;
  drawerRoot: null;
  collapseItemButton: null;
  createCollectionButton: null;
  props: DrawerProps;

  componentDidMount() {
    const { onDrawerClose, dispatch } = this.props;
    this.drawer = new MDCTemporaryDrawer(this.drawerRoot);
    this.drawer.listen('MDCTemporaryDrawer:close', onDrawerClose);
    this.updateRequirements();

    // Attach click listeners here; this is a necessary hack to get around MDC limitations
    if (this.collapseItemButton) {
      // make flow happy
      this.collapseItemButton.addEventListener('click', (event: MouseEvent) => {
        event.preventDefault();
        onDrawerClose();
      }, false);
    }

    // this will be undefined if SETTINGS.editable is false
    if (this.createCollectionButton) {
      this.createCollectionButton.addEventListener('click', (event: MouseEvent) => {
        event.preventDefault();

        onDrawerClose();
        dispatch(collectionUiActions.startNewCollectionDialog());
      }, false);
    }
  }

  componentWillUnmount() {
    if (this.drawer) {
      this.drawer.destroy();
    }
  }

  updateRequirements = () => {
    const { dispatch, needsUpdate } = this.props;
    if (needsUpdate) {
      dispatch(actions.collectionsList.get());
    }
  };

  componentWillReceiveProps(nextProps: DrawerProps) {
    if (this.drawer) {
      if (this.props.open !== nextProps.open) {
        this.drawer.open = nextProps.open;
      }
    }
  }

  render() {
    const { collections } = this.props;
    return <aside className="mdc-temporary-drawer mdc-typography" ref={div => this.drawerRoot = div}>
      <nav className="mdc-temporary-drawer__drawer">
        <nav id="nav-username" className="mdc-temporary-drawer__content mdc-list">
          <a id="collapse_item" className="mdc-list-item mdc-link" href="#" ref={
            node => this.collapseItemButton = node
          }>
            {SETTINGS.user}
          </a>
        </nav>
        <header className="mdc-temporary-drawer__header">
          <div className="mdc-temporary-drawer__header-content">
            Collections
          </div>
        </header>
        <nav id="nav-collections" className="mdc-temporary-drawer__content mdc-list">
          {collections.map(col =>
            <a
              className="mdc-list-item mdc-temporary-drawer--selected"
              href={makeCollectionUrl(col.key)}
              key={col.key}
            >
              { col.title }
            </a>
          )}
          {
            SETTINGS.editable ?
              <span>
                <button className="create-collection-button" ref={node => this.createCollectionButton = node}>
                  <span className="plus">+</span> Create a Collection
                </button>
              </span>
              : null
          }
        </nav>
        <nav id="icon-with-text-demo" className="mdc-temporary-drawer__content mdc-list">
          <a className="mdc-list-item mdc-link" href="/logout/">
            <i className="material-icons mdc-list-item__start-detail" aria-hidden="true">input</i>
            Log out
          </a>
        </nav>
      </nav>
    </aside>;
  }
}

const mapStateToProps = (state) => {
  const { collectionsList, commonUi } = state;
  const collections = collectionsList.loaded ? collectionsList.data : [];
  const needsUpdate = !collectionsList.processing && !collectionsList.loaded;

  return {
    collections,
    needsUpdate,
    commonUi
  };
};

export default connect(mapStateToProps)(Drawer);
