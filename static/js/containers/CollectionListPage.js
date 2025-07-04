// @flow
/* global SETTINGS: false */

import React from "react"
import * as R from "ramda"
import { connect } from "react-redux"
import type { Dispatch } from "redux"
import { Link } from "react-router-dom"

import { DIALOGS } from "../constants"
import * as collectionUiActions from "../actions/collectionUi"
import { actions } from "../actions"
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
    isAdmin: boolean,
    commonUi: CommonUiState
  }

  render() {
    return (
      <div className="collection-list-content">
        <div className="card centered-content">
          <h1 className="mdc-typography--title">My Collections</h1>
          {this.renderSearchInput()}
          {this.renderCollectionLinks()}
          {this.renderPaginator()}
          {this.renderFormLink()}
        </div>
      </div>
    )
  }

  renderPaginator() {
    const { collectionsPagination } = this.props
    const { currentPage, numPages } = collectionsPagination
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
    return SETTINGS.is_app_admin ? (
      <a
        className="button-link create-collection-button"
        onClick={this.openNewCollectionDialog.bind(this)}
      >
        <i className="material-icons">add</i>
        Create New Collection
      </a>
    ) : null
  }

  renderSearchInput() {
    // Get initial search value from URL if present
    const params = new URLSearchParams(window.location.search)
    const searchQuery = params.get('search') || ''

    return (
      <div className="collection-search">
        <div className="mdc-text-field mdc-text-field--fullwidth">
          <input
            type="text"
            className="mdc-text-field__input"
            placeholder="Search collections..."
            defaultValue={searchQuery}
            onChange={e => this.handleSearch(e.target.value)}
          />
        </div>
      </div>
    )
  }

  handleSearch(searchText) {
    // Reset to page 1 when searching
    if (this.props.collectionsPagination.currentPage !== 1) {
      this.props.collectionsPagination.setCurrentPage(1)
    }

    // Update URL with search params
    const params = new URLSearchParams(window.location.search)
    if (searchText) {
      params.set('search', searchText)
    } else {
      params.delete('search')
    }

    // Push new URL without reloading the page
    const newUrl = `${window.location.pathname}?${params.toString()}`
    window.history.pushState({ path: newUrl }, '', newUrl)

    // Trigger a re-fetch of collections with the search parameter
    this.props.dispatch(actions.collectionsPagination.getPage({ page: 1 }))
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
      return <ErrorMessages.UnableToLoadData />
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
                  {collection.video_count} Videos | Owner: {collection.owner_info.username}
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
