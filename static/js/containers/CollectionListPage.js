// @flow
/* global SETTINGS: false */

import React from 'react';
import { connect } from 'react-redux';
import type { Dispatch } from "redux";
import { Link } from "react-router-dom";

import { actions } from '../actions';
import OVSToolbar from '../components/OVSToolbar';
import Footer from '../components/Footer';
import { makeCollectionUrl } from "../lib/urls";

import type { Collection } from "../flow/collectionTypes";

class CollectionListPage extends React.Component {
  props: {
    dispatch: Dispatch,
    collections: Array<Collection>,
    editable: boolean,
    needsUpdate: boolean,
  };

  componentDidMount() {
    this.updateRequirements();
  }

  componentDidUpdate() {
    this.updateRequirements();
  }

  updateRequirements = () => {
    const { dispatch, needsUpdate } = this.props;
    if (needsUpdate) {
      dispatch(actions.collectionsList.get());
    }
  };

  renderCollectionLinks() {
    const { collections } = this.props;

    if (collections.length === 0) return null;

    return <ul>
      {collections.map((collection) => (
        <li key={collection.key}>
          <Link to={makeCollectionUrl(collection.key)}>
            {collection.title}
          </Link>
          &nbsp;&nbsp;
          <a
            href={`/collection_upload/${collection.key}`}
            target="_blank"
            className="material-icons"
          >
            file_upload
          </a>
        </li>
      ))}
    </ul>;
  }

  render() {
    const formLink = SETTINGS.editable
      ? (
        <a href="/collection_form" target="_blank">
          Create New Collection&nbsp;
          <i className="material-icons">library_add</i>
        </a>
      )
      : null;

    return <div>
      <OVSToolbar setDrawerOpen={() => {}} />
      <div className="collection-list-content">
        <h2>Collections</h2>
        { this.renderCollectionLinks() }
        { formLink }
      </div>
      <Footer />
    </div>;
  }
}

const mapStateToProps = (state) => {
  const { collectionsList } = state;
  const collections = collectionsList.loaded ? collectionsList.data : [];
  const needsUpdate = !collectionsList.processing && !collectionsList.loaded;

  return {
    collections,
    needsUpdate
  };
};

export default connect(mapStateToProps)(CollectionListPage);
