import React from 'react'
import R from "ramda"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import { actions } from "../actions"


export const withPagedCollections = (WrappedComponent) => {
  return class WithPagedCollections extends React.Component {
    props: {
      dispatch: Dispatch,
    }

    render() {
      return (
        <WrappedComponent
          {...this.props}
          setCurrentPage={this.setCurrentPage.bind(this)}
        />
      )
    }

    setCurrentPage (nextCurrentPage: number) {
      this.props.dispatch(actions.collectionsPagination.setCurrentPage({
        currentPage: nextCurrentPage
      }))
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
          page: this.props.collectionsPagination.currentPage,
        })
      )
    }
  }
}

export const mapStateToProps = (state) => {
  const { collectionsPagination } = state
  const { currentPage, pages } =  collectionsPagination
  const collectionsCurrentPageNeedsUpdate = (
    pages && (pages[currentPage] === undefined)
  )
  return {
    collectionsPagination,
    collectionsCurrentPageNeedsUpdate,
  }
}

export default R.compose(
  connect(mapStateToProps),
  withPagedCollections
)
