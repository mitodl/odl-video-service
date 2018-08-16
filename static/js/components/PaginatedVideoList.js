// @flow

/*
 * (2018-05-11, dorska)
 * This is an ersatz paginated list. I say ersatz because it doesn't pull pages
 * from a backend service. Instead it does the pagination internally.
 *
 * I think this is what we want for now; most collections do not have
 * large numbers of videos, so the complexity of making an additional query
 * and tracking video pagination in global app state doesn't seem worth it to me.
 *
 * However, if we later want to do full backend pagination for videos, we can
 * just swap-out how you get the pagination object. For example, by making
 * this a connected component that selects pagination data from the global
 * state. See static/js/containers/withPagedCollections.js for an example.
*/

import React from "react"
import _ from "lodash"

import Paginator from "./Paginator"
import VideoList from "./VideoList"

import type { Pagination } from "../flow/paginationTypes"


export class PaginatedVideoList extends React.Component<*, *> {
  props: {
    className?: string,
    style?: {[string]: any},
    videos: Array<Video>,
    pageSize: number,
  }

  state: {
    currentPage: number
  }

  static defaultProps = {
    pageSize: 8
  }

  constructor(props:any) {
    super(props)
    this.state = {
      currentPage: 1
    }
  }

  render () {
    const className = `paginated-video-list ${this.props.className || ''}`
    const { videos } = this.props
    return (
      <div className={className} style={this.props.style}>
        {
          _.isEmpty(videos) ?
            this.renderEmptyMessage()
            : this.renderBody()
        }
      </div>
    )
  }

  renderEmptyMessage () {
    return (<div className="empty-message"></div>)
  }

  renderBody () {
    const pagination = this.selectPagination(this.props.videos, this.props.pageSize)
    return (
      <div className="paginated-video-list-body">
        {this.renderListForCurrentPage(pagination)}
        {this.renderPaginator(pagination)}
      </div>
    )
  }

  selectPagination (videos:Array<Video>, pageSize:number):Pagination {
    const count = videos.length
    const numPages = Math.ceil(count / pageSize)
    const pages = {}
    for (let i = 0; i < numPages; i++) {
      const pageStart = i * pageSize
      const pageEnd = pageStart + pageSize
      // 1-based indexing
      pages[i + 1] = {items: videos.slice(pageStart, pageEnd)}
    }
    const currentPage = this.state.currentPage
    const pagination = {
      count,
      currentPage,
      currentPageData: pages[currentPage],
      numPages,
      pages,
      setCurrentPage:  (newCurrentPage:number) => {
        this.setState({currentPage: newCurrentPage})
      },
    }
    return pagination
  }

  renderListForCurrentPage (pagination:Pagination) {
    const passThroughProps = _.omit(
      this.props, 
      ['className', 'style', 'videos', 'pageSize']
    )
    return (
      <VideoList
        // $FlowFixMe: we will have currentPageData.
        videos={pagination.currentPageData.items}
        {...passThroughProps}
      />
    )
  }

  renderPaginator (pagination:Pagination) {
    return (
      <Paginator
        currentPage={pagination.currentPage}
        totalPages={pagination.numPages}
        // $FlowFixMe: we will have setCurrentPage.
        onClickPrev={() => pagination.setCurrentPage(pagination.currentPage - 1)}
        // $FlowFixMe: we will have setCurrentPage.
        onClickNext={() => pagination.setCurrentPage(pagination.currentPage + 1)}
        style={{float: 'right'}}
      />
    )
  }
}

export default PaginatedVideoList
