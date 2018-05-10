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
import type { Collection, CollectionsPagination } from "../flow/collectionTypes"
import withPagedCollections from "./withPagedCollections"
import LoadingIndicator from "../components/material/LoadingIndicator"
import Paginator from "../components/Paginator"
import * as ErrorMessages from "../components/errorMessages"

export class CollectionListPage extends React.Component<*, void> {
  props: {
    collectionsPagination: CollectionsPagination,
    dispatch: Dispatch,
    collections: Array<Collection>,
    editable: boolean,
    commonUi: CommonUiState
  }

  render() {
    return (
      <div className="collection-list-content">
        <div className="card centered-content">
          <h1 className="mdc-typography--title">My Collections</h1>
          {this.renderCollectionLinks()}
          {this.renderPaginator()}
          {this.renderFormLink()}
        </div>
      </div>
    )
  }

  renderPaginator() {
    const { collectionsPagination } = this.props
    const { currentPage, numPages, currentPageData } = collectionsPagination
    if (currentPageData) {
      currentPageData
    }
    return (
      <Paginator
        currentPage={currentPage}
        totalPages={numPages}
        onClickNext={() => this.incrementCurrentPage(1)}
        onClickPrev={() => this.incrementCurrentPage(-1)}
      />
    )
  }

  incrementCurrentPage(amount: number) {
    const { currentPage, setCurrentPage } = this.props.collectionsPagination
    if (setCurrentPage) {
      setCurrentPage(currentPage + amount)
    }
  }

  renderFormLink() {
    return SETTINGS.editable ? (
      <a
        className="button-link create-collection-button"
        onClick={this.openNewCollectionDialog.bind(this)}
      >
        <i className="material-icons">add</i>
        Create New Collection
      </a>
    ) : null
  }

  openNewCollectionDialog() {
    const { dispatch } = this.props
    dispatch(collectionUiActions.showNewCollectionDialog())
  }

  renderCollectionLinks() {
    const { currentPageData } = this.props.collectionsPagination
    if (!currentPageData) {
      return null
    }
    if (currentPageData.status === "ERROR") {
      return (<ErrorMessages.UnableToLoadData/>)
    } else if (currentPageData.status === "LOADING") {
      return <LoadingIndicator />
    } else if (currentPageData.status === "LOADED") {
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

export class CollectionListPageWithDrawer extends React.Component<*, void> {
  render() {
    return (
      <WithDrawer>
        <CollectionListPage {...this.props} />
      </WithDrawer>
    )
  }
}

const mapStateToProps = state => {
  return {
    commonUi: state.commonUi
  }
}

export const ConnectedCollectionListPage = R.compose(
  connect(mapStateToProps),
  withDialogs([
    { name: DIALOGS.COLLECTION_FORM, component: CollectionFormDialog }
  ]),
  withPagedCollections
)(CollectionListPageWithDrawer)

export default ConnectedCollectionListPage
