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
import type { Collection, CollectionsPagination, EdxEndpointList } from "../flow/collectionTypes"
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
    commonUi: CommonUiState,
    edxEndpoints: {
      data: ?EdxEndpointList,
      status: string
    },
    selectedEndpoint: ?number
  }

  constructor(props) {
    super(props)
    this.state = {
      viewMode: "endpoints" // "endpoints" or "collections"
    }

    // Bind methods
    this.handleBackToEndpoints = this.handleBackToEndpoints.bind(this)
    this.selectEndpoint = this.selectEndpoint.bind(this)
  }

  componentDidMount() {
    this.props.dispatch(actions.edxEndpoints.getEndpoints())

    // Check if URL already has an endpoint parameter
    const params = new URLSearchParams(window.location.search)
    if (params.get('edx_endpoint')) {
      this.setState({ viewMode: "collections" })
    }
  }

  componentDidUpdate(prevProps) {
    // If the selected endpoint changed from outside this component
    // (e.g., browser navigation), update the view mode accordingly
    if (prevProps.selectedEndpoint !== this.props.selectedEndpoint) {
      this.setState({
        viewMode: this.props.selectedEndpoint !== null ? "collections" : "endpoints"
      })
    }
  }

  render() {
    const { viewMode } = this.state
    const { selectedEndpoint, edxEndpoints } = this.props

    let title = "Collections by Endpoint"
    // Show endpoint name in title when in collection view
    if (viewMode === "collections" && selectedEndpoint !== null && edxEndpoints.data) {
      const selectedEndpointData = edxEndpoints.data.find(ep => ep.id === selectedEndpoint)
      if (selectedEndpointData) {
        title = selectedEndpointData.name
      } else {
        title = "All Collections"
      }
    }

    return (
      <div className="collection-list-content">
        <div className="card centered-content">
          <h1 className="mdc-typography--title">{title}</h1>

          {viewMode === "endpoints" ? (
            // Show only endpoints in endpoint view mode
            <div>
              {this.renderEdxEndpoints()}
              {this.renderFormLink()}
            </div>
          ) : (
            // Show back button, search, collections, and paginator in collection view mode
            <div>
              {this.renderBackToEndpoints()}
              {this.renderSearchInput()}
              {this.renderCollectionLinks()}
              {this.renderPaginator()}
              {this.renderFormLink()}
            </div>
          )}
        </div>
      </div>
    )
  }

  renderBackToEndpoints() {
    return (
      <div className="back-to-endpoints">
        <a
          className="button-link"
          onClick={this.handleBackToEndpoints}
        >
          <i className="material-icons">arrow_back</i>
          Back
        </a>
      </div>
    )
  }
  handleBackToEndpoints() {
    // Clear the endpoint parameter from URL
    const params = new URLSearchParams(window.location.search)
    params.delete('edx_endpoint')
    params.delete('search')

    // Push new URL without reloading the page
    const newUrl = `${window.location.pathname}?${params.toString()}`
    window.history.pushState({ path: newUrl }, '', newUrl)

    this.setState({ viewMode: "endpoints" })
  }

  renderEdxEndpoints() {
    const { edxEndpoints } = this.props
    if (!edxEndpoints || edxEndpoints.status === "INITIAL" || edxEndpoints.status === "LOADING") {
      return <LoadingIndicator />
    } else if (edxEndpoints.status === "ERROR") {
      return <ErrorMessages.UnableToLoadData />
    } else if (edxEndpoints.status === "LOADED" && edxEndpoints.data && edxEndpoints.data.length > 0) {
      return (
        <div className="edx-endpoints-container landing-view">
          <ul className="mdc-list mdc-list--two-line mdc-list--avatar-list endpoint-list">
            <li
              key="all"
              className="mdc-list-item endpoint-item"
              onClick={() => this.selectEndpoint(null)}
            >
              <span className="mdc-list-item__graphic grey-bg">
                <i className="material-icons" aria-hidden="true">folder</i>
              </span>
              <span className="mdc-list-item__text">
                All Collections
                <span className="mdc-list-item__secondary-text">
                  Access all available collections
                </span>
              </span>
            </li>
            {edxEndpoints.data.map(endpoint => (
              <li
                key={endpoint.id}
                className="mdc-list-item endpoint-item"
                onClick={() => this.selectEndpoint(endpoint.id)}
              >
                <span className="mdc-list-item__graphic grey-bg">
                  <i className="material-icons" aria-hidden="true">folder</i>
                </span>
                <span className="mdc-list-item__text">
                  {endpoint.name}
                  <span className="mdc-list-item__secondary-text">
                    {endpoint.base_url}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )
    }
    return null
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

  selectEndpoint(endpointId) {
    // Reset to page 1 when changing endpoint
    if (this.props.collectionsPagination.currentPage !== 1) {
      this.props.collectionsPagination.setCurrentPage(1)
    }

    // Update URL with endpoint param
    const params = new URLSearchParams(window.location.search)
    if (endpointId !== null) {
      params.set('edx_endpoint', endpointId)
    } else {
      params.delete('edx_endpoint')
    }

    // Push new URL without reloading the page
    const newUrl = `${window.location.pathname}?${params.toString()}`
    window.history.pushState({ path: newUrl }, '', newUrl)

    // Change view mode to collections
    this.setState({ viewMode: "collections" })

    // Trigger a re-fetch of collections with the endpoint filter
    this.props.dispatch(actions.collectionsPagination.getPage({ page: 1 }))
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
        <ul className="mdc-list mdc-list--two-line mdc-list--avatar-list collection-list">
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
  // Extract edx_endpoint from URL if present
  const params = new URLSearchParams(window.location.search)
  const selectedEndpoint = params.get('edx_endpoint') ? Number(params.get('edx_endpoint')) : null

  return {
    commonUi:         state.commonUi,
    edxEndpoints:     state.edxEndpoints,
    selectedEndpoint: selectedEndpoint
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
