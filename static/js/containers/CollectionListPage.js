// @flow
/* global SETTINGS: false */

import React from 'react';
import R from 'ramda';
import { connect } from 'react-redux';
import type { Dispatch } from "redux";
import { Link } from "react-router-dom";

import { DIALOGS } from "../constants";
import * as commonUiActions from '../actions/commonUi';
import * as collectionUiActions from '../actions/collectionUi';
import OVSToolbar from '../components/OVSToolbar';
import Drawer from '../components/material/Drawer';
import Footer from '../components/Footer';
import CollectionFormDialog from "../components/dialogs/CollectionFormDialog";
import { withDialogs } from "../components/dialogs/hoc";
import { makeCollectionUrl } from "../lib/urls";
import type { CommonUiState } from "../reducers/commonUi";
import type { Collection } from "../flow/collectionTypes";

class CollectionListPage extends React.Component {
  props: {
    dispatch: Dispatch,
    collections: Array<Collection>,
    editable: boolean,
    needsUpdate: boolean,
    commonUi: CommonUiState
  };

  setDrawerOpen = (open: boolean): void => {
    const { dispatch } = this.props;
    dispatch(commonUiActions.setDrawerOpen(open));
  };

  renderCollectionLinks() {
    const { collections } = this.props;

    if (collections.length === 0) return null;

    return <ul className="mdc-list mdc-list--two-line mdc-list--avatar-list">
      {collections.map((collection) => (
        <li key={collection.key} className="mdc-list-item">
          <span className="mdc-list-item__start-detail grey-bg">
            <i className="material-icons" aria-hidden="true">folder</i>
          </span>
          <span className="mdc-list-item__text">
            <Link to={makeCollectionUrl(collection.key)}>
              {collection.title}
            </Link>
          </span>
        </li>
      ))}
    </ul>;
  }

  openNewCollectionDialog = (e: MouseEvent) => {
    const { dispatch } = this.props;

    e.preventDefault();
    dispatch(collectionUiActions.startNewCollectionDialog());
  };

  render() {
    const { commonUi } = this.props;
    const formLink = SETTINGS.editable
      ? (
        <a href="#" className="button-link create-collection-button" onClick={this.openNewCollectionDialog}>
          Create New Collection&nbsp;
          <i className="material-icons">library_add</i>
        </a>
      )
      : null;

    return <div>
      <OVSToolbar setDrawerOpen={this.setDrawerOpen.bind(this, true)} />
      <Drawer open={commonUi.drawerOpen} onDrawerClose={this.setDrawerOpen.bind(this, false)} />
      <div className="collection-list-content">
        <div className="card centered-content">
          <h2 className="mdc-typography--title">My Collections</h2>
          { this.renderCollectionLinks() }
          { formLink }
        </div>
      </div>
      <Footer />
    </div>;
  }
}

const mapStateToProps = (state) => {
  const { collectionsList, commonUi } = state;
  const collections = collectionsList.loaded ? collectionsList.data : [];
  const needsUpdate = !collectionsList.processing && !collectionsList.loaded;

  return {
    collections,
    commonUi,
    needsUpdate
  };
};

export default R.compose(
  connect(mapStateToProps),
  withDialogs([
    {name: DIALOGS.NEW_COLLECTION, component: CollectionFormDialog},
  ])
)(CollectionListPage);
