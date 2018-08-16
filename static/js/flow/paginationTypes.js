// @flow

export type Page = {
  items:       Array<any>,
  status:      string,
  startIndex?: number,
  endIndex?:   number,
}

export type Pagination = {
  count: number,
  currentPage: number,
  currentPageData?: Page,
  numPages?: number,
  pages: {
    [string|number]: Page,
  },
  setCurrentPage?: (nextCurrentPage: number) => void,
}
