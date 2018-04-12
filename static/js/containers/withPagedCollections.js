import React from 'react'

import { actions } from "../actions"


export const withPagedCollections = (WrappedComponent) => {
  return class WithPagedCollections extends React.Component {
    render() {
      return (
        <WrappedComponent {...this.props} />
      )
    }

    componentDidMount () {
      this.updateCollectionsCurrentPageIfNeeded()
    }

    componentDidUpdate () {
      this.updateCollectionsCurrentPageIfNeeded()
    }

    updateCollectionsCurrentPageIfNeeded () {
      if (this.props.collectionsCurrentPageNeedsUpdate) {
        this.updateCollectionsCurrentPage()
      }
    }

    updateCollectionsCurrentPage () {
      this.props.dispatch(
        actions.collectionsPagination.getPage({
          page: this.props.collectionsCurrentPage,
        })
      )
    }
  }
}

export const mapStateToProps = (state) => {
  const { collectionsPagination } = state
  const { count, currentPage, pages } =  collectionsPagination
  const collectionsCurrentPageNeedsUpdate = (
    pages && (pages[currentPage] === undefined)
  )
  const collectionsCurrentPageData = (
    (pages && pages[currentPage])
    ? pages[currentPage]
    : undefined
  )
  return {
    collectionsCount:       count,
    collectionsCurrentPage: currentPage,
    collectionsCurrentPageData,
    collectionsCurrentPageNeedsUpdate,
  }
}

export default withPagedCollections
