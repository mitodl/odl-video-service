import React from "react"
import _ from "lodash"
import R from "ramda"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import { actions } from "../actions"


export const withPagedCollections = (WrappedComponent) => {
  return class WithPagedCollections extends React.Component<*, void> {
    props: {
      dispatch: Dispatch,
    }
    constructor (props) {
      super(props)
      this.setCurrentPage = this.setCurrentPage.bind(this)
    }

    render() {
      return (
        <WrappedComponent {...this.generatePropsForWrappedComponent()}/>
      )
    }

    generatePropsForWrappedComponent () {
      return {
        ...(_.omit(this.props, ["needsUpdate"])),
        collectionsPagination: {
          ...this.props.collectionsPagination,
          setCurrentPage:  this.setCurrentPage,
          currentPageData: this.getCurrentPageData(),
        }
      }
    }

    setCurrentPage (nextCurrentPage: number) {
      this.props.dispatch(actions.collectionsPagination.setCurrentPage({
        currentPage: nextCurrentPage
      }))
    }

    getCurrentPageData () {
      const { collectionsPagination } = this.props
      if (collectionsPagination && collectionsPagination.pages
        && collectionsPagination.currentPage
      ) {
        return collectionsPagination.pages[collectionsPagination.currentPage]
      }
      return undefined
    }

    componentDidMount () {
      this.updateCurrentPageIfNeedsUpdate()
    }

    componentDidUpdate () {
      this.updateCurrentPageIfNeedsUpdate()
    }

    updateCurrentPageIfNeedsUpdate () {
      if (this.props.needsUpdate) {
        this.updateCurrentPage()
      }
    }

    updateCurrentPage () {
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
  const needsUpdate = (pages && (pages[currentPage] === undefined))
  return {
    collectionsPagination,
    needsUpdate
  }
}

export default R.compose(
  connect(mapStateToProps),
  withPagedCollections
)
