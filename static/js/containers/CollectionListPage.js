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

class CollectionListPage extends React.Component<*, void> {
  props: {
    dispatch: Dispatch,
    collections: Array<Collection>,
    editable: boolean,
    needsUpdate: boolean,
    commonUi: CommonUiState
  }

  renderCollectionLinks() {
    const { collections } = this.props

    if (collections.length === 0) return null

    return (
      <ul className="mdc-list mdc-list--two-line mdc-list--avatar-list">
        {collections.map(collection => (
          <li key={collection.key} className="mdc-list-item">
            <span className="mdc-list-item__start-detail grey-bg">
              <i className="material-icons" aria-hidden="true">
                folder
              </i>
            </span>
            <span className="mdc-list-item__text">
              <Link to={makeCollectionUrl(collection.key)}>
                {collection.title}
              </Link>
              <span className="mdc-list-item__text__secondary">
                {collection.video_count} Videos
              </span>
            </span>
          </li>
        ))}
      </ul>
    )
  }

  openNewCollectionDialog = () => {
    const { dispatch } = this.props

    dispatch(collectionUiActions.showNewCollectionDialog())
  }

  render() {
    const formLink = SETTINGS.editable ? (
      <a
        className="button-link create-collection-button"
        onClick={this.openNewCollectionDialog}
      >
        <i className="material-icons">add</i>
        Create New Collection
      </a>
    ) : null

    return (
      <WithDrawer>
        <div className="collection-list-content">
          <div className="card centered-content">
            <h1 className="mdc-typography--title">My Collections</h1>
            {this.renderCollectionLinks()}
            {formLink}
          </div>
        </div>
      </WithDrawer>
    )
  }
}

const mapStateToProps = state => {
  const { collectionsList, commonUi } = state
  const collections = collectionsList.loaded ? collectionsList.data : []
  const needsUpdate = !collectionsList.processing && !collectionsList.loaded

  return {
    collections,
    commonUi,
    needsUpdate
  }
}

export default R.compose(
  connect(mapStateToProps),
  withDialogs([
    { name: DIALOGS.COLLECTION_FORM, component: CollectionFormDialog }
  ])
)(CollectionListPage)
