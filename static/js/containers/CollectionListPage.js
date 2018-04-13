// @flow
/* global SETTINGS: false */

import React from "react"
import R from "ramda"
import { connect } from "react-redux"
import type { Dispatch } from "redux"
import { Link } from "react-router-dom"

import { DIALOGS } from "../constants"
import * as collectionUiActions from "../actions/collectionUi"
import WithDrawer from "./WithDrawer"
import CollectionFormDialog from "../components/dialogs/CollectionFormDialog"
import { withDialogs } from "../components/dialogs/hoc"
import { makeCollectionUrl } from "../lib/urls"
import type { CommonUiState } from "../reducers/commonUi"
import type { Collection } from "../flow/collectionTypes"
import withPagedCollections from './withPagedCollections'
import LoadingIndicator from "../components/material/LoadingIndicator"

class CollectionListPage extends React.Component<*, void> {
  props: {
    dispatch: Dispatch,
    collections: Array<Collection>,
    editable: boolean,
    commonUi: CommonUiState
  }

  render() {
    return (
      <WithDrawer>
        <div className="collection-list-content">
          <div className="card centered-content">
            <h1 className="mdc-typography--title">My Collections</h1>
            {this.renderCollectionLinks()}
            {this.renderFormLink()}
          </div>
        </div>
      </WithDrawer>
    )
  }

  renderFormLink() {
    return (
      SETTINGS.editable ? (
        <a
        className="button-link create-collection-button"
        onClick={this.openNewCollectionDialog}
        >
        <i className="material-icons">add</i>
        Create New Collection
        </a>
      ) : null
    )
  }

  openNewCollectionDialog () {
    const { dispatch } = this.props
    dispatch(collectionUiActions.showNewCollectionDialog())
  }

  renderCollectionLinks() {
    const { collectionsPagination } = this.props
    const currentPageData = (
      collectionsPagination.pages[collectionsPagination.currentPage]
    )
    if (! currentPageData) {
      return null
    }
    if (currentPageData.status === 'ERROR') {
      return (<div>Error!</div>)
    } else if (currentPageData.status === 'LOADING') {
      return (<LoadingIndicator/>)
    }
    else if (currentPageData.status === 'LOADED') {
      const { collections } = currentPageData
      return (
        <ul className="mdc-list mdc-list--two-line mdc-list--avatar-list">
          {collections.map(collection => (
            <li key={collection.key} className="mdc-list-item">
              <span className="mdc-list-item__graphic grey-bg">
                <i className="material-icons" aria-hidden="true">
                  folder
                </i>
              </span>
              <span className="mdc-list-item__text">
                <Link to={makeCollectionUrl(collection.key)}>
                  {collection.title}
                </Link>
                <span className="mdc-list-item__secondary-text">
                  {collection.video_count} Videos
                </span>
              </span>
            </li>
          ))}
        </ul>
      )
    }
  }

}

const mapStateToProps = state => {
  return {
    commonUi: state.commonUi
  }
}

export default R.compose(
  connect(mapStateToProps),
  withPagedCollections
)(CollectionListPage)
