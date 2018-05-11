// @flow
import React from "react"
import _ from "lodash"
import sinon from "sinon"
import { shallow } from "enzyme"
import { assert } from "chai"
import { makeVideo } from "../factories/video"

import PaginatedVideoList from "./PaginatedVideoList"


describe("PaginatedVideoList", () => {
  let sandbox, defaultProps, instance, wrapper

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    defaultProps = {
      videos: [...Array(3).keys()].map(() => makeVideo()),
    }
  })

  afterEach(() => {
    sandbox.restore()
  })

  const stubRenderingMethod = methodName => {
    sandbox
      .stub(PaginatedVideoList.prototype, methodName)
      .returns(<i id={`mocked-${methodName}`} key={`mocked-${methodName}`} />)
  }

  const stubRenderingMethods = methodNames => {
    methodNames.forEach(methodName => stubRenderingMethod(methodName))
  }

  const makePaginatedVideoListInstance = (props = {}) => {
    return shallow(<PaginatedVideoList {...defaultProps} {...props}/>).instance()
  }

  const makePagination = () => {
    const mockPagination = {
      count:           42,
      numPages:        42,
      currentPage:     42,
      currentPageData: {
        items: [...Array(3).keys()].map(() => makeVideo()),
      },
      pages:          {},
      setCurrentPage: sinon.stub(),
    }
    return mockPagination
  }

  describe("constructor", () => {
    it("sets initial currentPage", () => {
      const instance = makePaginatedVideoListInstance()
      assert.equal(instance.state.currentPage, 1)
    })
  })

  describe("render", () => {

    const render = (props = {}) => {
      return shallow(<PaginatedVideoList {...defaultProps} {...props} />)
    }

    beforeEach(() => {
      stubRenderingMethods(['renderEmptyMessage', 'renderBody'])
    })

    describe("when videos is empty", () => {
      const emptyVideosValues = [null, undefined, []]
      _.forEach(emptyVideosValues, (videos) => {
        it(`renders empty message when videos is ${JSON.stringify(videos)}`, () => {
          const wrapper = render({videos})
          assert.isTrue(wrapper.find('#mocked-renderEmptyMessage').exists())
          assert.isFalse(wrapper.find('#mocked-renderBody').exists())
        })
      })
    })

    describe("when videos is not empty", () => {
      it("renders body", () => {
        const videos = defaultProps.videos
        const wrapper = render({videos})
        assert.isTrue(wrapper.find('#mocked-renderBody').exists())
        assert.isFalse(wrapper.find('#mocked-renderEmptyMessage').exists())
      })
    })
  })

  describe("renderBody", () => {
    beforeEach(() => {
      sandbox.stub(PaginatedVideoList.prototype, 'selectPagination')
      stubRenderingMethods(['renderListForCurrentPage', 'renderPaginator'])
      instance = makePaginatedVideoListInstance()
      wrapper = shallow(instance.renderBody())
    })

    it("gets pagination object", () => {
      sinon.assert.calledWith(instance.selectPagination, instance.props.videos)
    })

    it("renders list for current page", () => {
      assert.isTrue(wrapper.find('#mocked-renderListForCurrentPage').exists())
      sinon.assert.calledWith(
        instance.renderListForCurrentPage,
        instance.selectPagination.returnValues[0]
      )
    })

    it("renders paginator", () => {
      assert.isTrue(wrapper.find('#mocked-renderPaginator').exists())
      sinon.assert.calledWith(
        instance.renderPaginator,
        instance.selectPagination.returnValues[0]
      )
    })
  })

  describe("selectPagination", () => {
    const pageSize = 3
    const numPages = 3
    const numVideos = (pageSize * numPages) - (pageSize - 1) // partial last page
    const videos = [...Array(numVideos).keys()].map(() => makeVideo())
    const currentPage = 2
    let actualPagination

    beforeEach(() => {
      instance = makePaginatedVideoListInstance({videos, pageSize})
      instance.setState({currentPage})
      actualPagination = instance.selectPagination(videos, pageSize)
    })

    it("returns expected pagination object", () => {
      const expectedPages = {}
      for (let i = 0; i < numPages; i++) {
        const pageStart = pageSize * i
        const pageEnd = pageStart + pageSize
        expectedPages[i + 1] = {items: videos.slice(pageStart, pageEnd)}
      }
      const expectedSimplePaginationAttrs = {
        count:           numVideos,
        currentPage,
        currentPageData: expectedPages[currentPage],
        numPages,
        pages:           expectedPages,
      }
      assert.deepEqual(
        _.pick(actualPagination, Object.keys(expectedSimplePaginationAttrs)),
        expectedSimplePaginationAttrs
      )
    })

    it("pagination.setCurrentPage updates state", () => {
      actualPagination.setCurrentPage(1)
      assert.equal(instance.state.currentPage, 1)
      actualPagination.setCurrentPage(2)
      assert.equal(instance.state.currentPage, 2)
    })
  })

  describe("renderListForCurrentPage", () => {
    it("renders VideoList w/ expected props", () => {
      const randomProps = {some: 'prop', someOther: 'prop'}
      instance = makePaginatedVideoListInstance({
        className: 'someClassName',
        pageSize:  3,
        style:     {color: 'blue'},
        ...randomProps
      })
      const mockPagination = makePagination()
      wrapper = shallow(
        <div>{instance.renderListForCurrentPage(mockPagination)}</div>
      )
      const videoList = wrapper.find('VideoList')
      const expectedProps = {
        videos: mockPagination.currentPageData.items,
        ...(_.omit(instance.props, ['className', 'style', 'videos', 'pageSize'])),
      }
      assert.deepEqual(videoList.props(), expectedProps)
    })
  })

  describe("renderPaginator", () => {
    let paginator, mockPagination

    beforeEach(() => {
      instance = makePaginatedVideoListInstance()
      mockPagination = makePagination()
      wrapper = shallow(
        <div>{instance.renderPaginator(mockPagination)}</div>
      )
      paginator = wrapper.find('Paginator')
    })

    it("has expected basic props", () => {
      const expectedBasicProps = {
        currentPage: mockPagination.currentPage,
        totalPages:  mockPagination.numPages,
      }
      assert.deepEqual(
        _.pick(paginator.props(), Object.keys(expectedBasicProps)),
        expectedBasicProps
      )
    })

    it("has click handlers", () => {
      paginator.prop('onClickPrev')()
      sinon.assert.calledWith(
        mockPagination.setCurrentPage,
        mockPagination.currentPage - 1
      )
      paginator.prop('onClickNext')()
      sinon.assert.calledWith(
        mockPagination.setCurrentPage,
        mockPagination.currentPage + 1
      )
    })
  })
})
