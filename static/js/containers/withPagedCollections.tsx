import React from "react"
import _ from "lodash"
import * as R from "ramda"
import { connect } from "react-redux"
import type { UnknownAction } from "redux"
import type { ThunkAction, ThunkDispatch } from "redux-thunk"

import { actions } from "../actions"
import type {
  CollectionsPage,
  CollectionsPagination
} from "../types/collectionTypes"
import type { RootState } from "../types/rootState"
import type { ActionCreator } from "../types/reduxTypes"

/*
 * `actions` is declared `Record<string, unknown>` in actions/index.ts, so each
 * slice comes back as `unknown`. The cast is erased at runtime -- every
 * dispatch below stays a property access on `actions.collectionsPagination`,
 * which is what withPagedCollections_test.js stubs -- and only tells tsc the
 * shape actions/collectionsPagination.ts already exports.
 */
type CollectionsPaginationActions = {
  setCurrentPage: ActionCreator
  getPage: (opts: {
    page: number
  }) => ThunkAction<Promise<void>, RootState, unknown, UnknownAction>
}

type Props = {
  dispatch: ThunkDispatch<RootState, unknown, UnknownAction>
  collectionsPagination: CollectionsPagination
  needsUpdate?: boolean
  // Every other prop is forwarded untouched to the wrapped component.
  [key: string]: unknown
}

export const withPagedCollections = (
  WrappedComponent: React.ComponentType<Record<string, unknown>>
) => {
  return class WithPagedCollections extends React.Component<Props> {
    constructor(props: Props) {
      super(props)
      this.setCurrentPage = this.setCurrentPage.bind(this)
    }

    render() {
      return <WrappedComponent {...this.generatePropsForWrappedComponent()} />
    }

    generatePropsForWrappedComponent() {
      return {
        ..._.omit(this.props, ["needsUpdate"]),
        collectionsPagination: {
          ...this.props.collectionsPagination,
          setCurrentPage:  this.setCurrentPage,
          currentPageData: this.getCurrentPageData()
        }
      }
    }

    setCurrentPage(nextCurrentPage: number) {
      const paginationActions =
        actions.collectionsPagination as CollectionsPaginationActions
      this.props.dispatch(
        paginationActions.setCurrentPage({
          currentPage: nextCurrentPage
        })
      )
    }

    getCurrentPageData(): CollectionsPage | undefined {
      const { collectionsPagination } = this.props
      if (
        collectionsPagination &&
        collectionsPagination.pages &&
        collectionsPagination.currentPage
      ) {
        return collectionsPagination.pages[collectionsPagination.currentPage]
      }
      return undefined
    }

    componentDidMount() {
      this.updateCurrentPageIfNeedsUpdate()
    }

    componentDidUpdate() {
      this.updateCurrentPageIfNeedsUpdate()
    }

    updateCurrentPageIfNeedsUpdate() {
      if (this.props.needsUpdate) {
        this.updateCurrentPage()
      }
    }

    updateCurrentPage() {
      const paginationActions =
        actions.collectionsPagination as CollectionsPaginationActions
      this.props.dispatch(
        paginationActions.getPage({
          page: this.props.collectionsPagination.currentPage
        })
      )
    }
  }
}

export const mapStateToProps = (state: RootState) => {
  const { collectionsPagination } = state
  const { currentPage, pages } = collectionsPagination
  const needsUpdate = pages && pages[currentPage] === undefined
  return {
    collectionsPagination,
    needsUpdate
  }
}

export default R.compose(connect(mapStateToProps), withPagedCollections)
