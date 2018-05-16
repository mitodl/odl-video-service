// @flow
/* global SETTINGS: false */
import React from "react"
import _ from "lodash"
import sinon from "sinon"
import { shallow } from "enzyme"
import { assert } from "chai"

import { mapStateToProps, CollectionDetailPage } from "./CollectionDetailPage"
import { actions } from "../actions"
import * as collectionUiActions from "../actions/collectionUi"
import * as commonUiActions from "../actions/commonUi"
import { makeCollection } from "../factories/collection"
import { DIALOGS } from "../constants"

describe("CollectionDetailPage", () => {
  let sandbox

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const stubRenderingMethod = methodName => {
    sandbox
      .stub(CollectionDetailPage.prototype, methodName)
      .returns(<i id={`mocked-${methodName}`} key={`mocked-${methodName}`} />)
  }

  const stubRenderingMethods = methodNames => {
    methodNames.forEach(methodName => stubRenderingMethod(methodName))
  }

  describe("mapStateToProps", () => {
    let state, ownProps

    beforeEach(() => {
      state = {
        collections: {},
        commonUi:    {}
      }
      ownProps = {
        match: {
          params: { collectionKey: "some_collectionKey" }
        }
      }
    })

    it("selects collectionKey", () => {
      const actualProps = mapStateToProps(state, ownProps)
      const expectedCollectionKey = ownProps.match.params.collectionKey
      assert.equal(actualProps.collectionKey, expectedCollectionKey)
    })

    describe("when selecting collection", () => {
      const testDefs = [
        { opts: { loaded: true, data: undefined }, expected: null },
        { opts: { loaded: true, data: "somedata" }, expected: "somedata" },
        { opts: { loaded: false, data: undefined }, expected: null },
        { opts: { loaded: false, data: "somedata" }, expected: null }
      ]
      testDefs.forEach(testDef => {
        const { opts, expected } = testDef
        // $FlowFixMe: we can coerce to string.
        it(`it selects collection as ${expected} when opts are ${JSON.stringify(
          opts
        )} `, () => {
          state = {
            ...state,
            collections: Object.assign({}, state.collections, {
              loaded: testDef.opts.loaded,
              data:   testDef.opts.data
            })
          }
          const actualProps = mapStateToProps(state, ownProps)
          assert.equal(actualProps.collection, testDef.expected)
        })
      })
    })

    describe("when selecting collectionError", () => {
      it("selects collections.error if present", () => {
        state = {
          ...state,
          collections: Object.assign({}, state.collections, {
            error: "someError"
          })
        }
        const actualProps = mapStateToProps(state, ownProps)
        assert.equal(actualProps.collectionError, state.collections.error)
      })

      it("selects null if collection.error empty", () => {
        state = {
          ...state,
          collections: Object.assign({}, state.collections, {
            error: undefined
          })
        }
        const actualProps = mapStateToProps(state, ownProps)
        assert.equal(actualProps.collectionError, null)
      })
    })

    describe("when selecting needsUpdate", () => {
      const collection = { key: "someKey" }
      const testDefs = [
        {
          opts:     { processing: true, loaded: true, matchKey: true },
          expected: false
        },
        {
          opts:     { processing: true, loaded: true, matchKey: false },
          expected: true
        },
        {
          opts:     { processing: true, loaded: false, matchKey: true },
          expected: false
        },
        {
          opts:     { processing: true, loaded: false, matchKey: false },
          expected: false
        },
        {
          opts:     { processing: false, loaded: true, matchKey: true },
          expected: false
        },
        {
          opts:     { processing: false, loaded: true, matchKey: false },
          expected: true
        },
        {
          opts:     { processing: false, loaded: false, matchKey: true },
          expected: true
        },
        {
          opts:     { processing: false, loaded: false, matchKey: false },
          expected: true
        }
      ]
      testDefs.forEach(testDef => {
        const { opts, expected } = testDef
        // $FlowFixMe: we can coerce to string.
        it(`it selects needsUpdate as ${expected} when opts are ${JSON.stringify(
          opts
        )} `, () => {
          ownProps = {
            ...ownProps,
            match: {
              params: {
                collectionKey: opts.matchKey ? collection.key : "otherKey"
              }
            }
          }
          state = {
            ...state,
            collections: Object.assign({}, state.collections, {
              processing: opts.processing,
              loaded:     opts.loaded,
              data:       collection
            })
          }
          const actualProps = mapStateToProps(state, ownProps)
          assert.equal(actualProps.needsUpdate, expected)
        })
      })
    })

    it("passes through commonUi", () => {
      state = {
        ...state,
        commonUi: { some: "value" }
      }
      const actualProps = mapStateToProps(state, ownProps)
      assert.equal(actualProps.commonUi, state.commonUi)
    })
  })

  describe("Component", () => {
    let collection, props, wrapper, page

    beforeEach(() => {
      collection = makeCollection()
      props = {
        dispatch:        sandbox.stub(),
        collection,
        collectionError: undefined,
        collectionKey:   collection.key,
        editable:        true,
        needsUpdate:     false,
        commonUi:        {},
        showDialog:      sandbox.stub()
      }
    })

    describe("render", () => {
      const render = (extraProps = {}) => {
        return shallow(
          <CollectionDetailPage {...{ ...props, ...extraProps }} />
        )
      }

      beforeEach(() => {
        stubRenderingMethods(["renderError", "renderBody"])
      })

      it("renders drawer", () => {
        wrapper = render()
        assert.isTrue(wrapper.find("Connect(WithDrawer)").exists())
      })

      describe("when there is an error", () => {
        beforeEach(() => {
          wrapper = render({ collectionError: "someError" })
        })

        it("renders error", () => {
          sinon.assert.calledWith(
            wrapper.instance().renderError,
            wrapper.instance().props.collectionError
          )
          sinon.assert.notCalled(wrapper.instance().renderBody)
        })
      })

      describe("when there is no error", () => {
        beforeEach(() => {
          wrapper = render({ collectionError: undefined })
        })

        it("renders body", () => {
          sinon.assert.called(wrapper.instance().renderBody)
          sinon.assert.notCalled(wrapper.instance().renderError)
        })
      })
    })

    describe("renderBody", () => {
      beforeEach(() => {
        stubRenderingMethods([
          "renderTools",
          "renderDescription",
          "renderVideos"
        ])
      })

      const renderBody = ({ extraProps = {} } = {}) => {
        page = new CollectionDetailPage({ ...props, ...extraProps })
        return shallow(page.renderBody())
      }

      it("renders tools", () => {
        assert.isTrue(
          renderBody()
            .find("#mocked-renderTools")
            .exists()
        )
      })

      it("renders description", () => {
        assert.isTrue(
          renderBody()
            .find("#mocked-renderDescription")
            .exists()
        )
      })

      it("renders videos", () => {
        assert.isTrue(
          renderBody()
            .find("#mocked-renderVideos")
            .exists()
        )
      })
    })

    describe("renderTools", () => {
      beforeEach(() => {
        stubRenderingMethods(["renderAdminTools"])
      })

      // $FlowFixMe: defaults are ok.
      const renderTools = ({ extraProps = {}, isAdmin = false } = {}) => {
        page = new CollectionDetailPage({ ...props, ...extraProps })
        return shallow(page.renderTools(isAdmin))
      }

      it("has tools class", () => {
        assert.isTrue(
          renderTools()
            .at(0)
            .hasClass("tools")
        )
      })

      it("renders admin tools if isAdmin", () => {
        assert.isTrue(
          renderTools({ isAdmin: true })
            .find("#mocked-renderAdminTools")
            .exists()
        )
      })

      it("does not render admin tools if not isAdmin", () => {
        assert.isFalse(
          renderTools({ isAdmin: false })
            .find("#mocked-renderAdminTools")
            .exists()
        )
      })
    })

    describe("renderAdminTools", () => {
      beforeEach(() => {
        stubRenderingMethods(["renderSettingsFrob", "renderUploadFrob"])
      })

      const renderAdminTools = ({ extraProps = {} } = {}) => {
        page = new CollectionDetailPage({ ...props, ...extraProps })
        return shallow(<div>{page.renderAdminTools()}</div>)
      }

      it("renders settings frob", () => {
        assert.isTrue(
          renderAdminTools()
            .find("#mocked-renderSettingsFrob")
            .exists()
        )
      })

      it("renders upload frob", () => {
        assert.isTrue(
          renderAdminTools()
            .find("#mocked-renderUploadFrob")
            .exists()
        )
      })
    })

    describe("renderSettingsFrob", () => {
      const renderSettingsFrob = ({ extraProps = {} } = {}) => {
        page = new CollectionDetailPage({ ...props, ...extraProps })
        return shallow(page.renderSettingsFrob())
      }

      it("has settings icon", () => {
        assert.equal(
          renderSettingsFrob()
            .find(".material-icons")
            .text(),
          "settings"
        )
      })

      it("triggers showEditCollectionDialog when clicked", () => {
        sandbox.stub(CollectionDetailPage.prototype, "showEditCollectionDialog")
        sinon.assert.notCalled(
          CollectionDetailPage.prototype.showEditCollectionDialog
        )
        renderSettingsFrob()
          .at(0)
          .simulate("click")
        sinon.assert.called(
          CollectionDetailPage.prototype.showEditCollectionDialog
        )
      })
    })

    describe("renderUploadFrob", () => {
      const renderUploadFrob = ({ extraProps = {} } = {}) => {
        page = new CollectionDetailPage({ ...props, ...extraProps })
        return shallow(<div>{page.renderUploadFrob()}</div>)
      }

      it("renders DropBoxChooser with expected simple props", () => {
        SETTINGS.dropbox_key = "someAppKey"
        const chooser = renderUploadFrob().find("DropboxChooser")
        const expectedSimpleProps = {
          appKey:      SETTINGS.dropbox_key,
          linkType:    "direct",
          multiselect: true,
          extensions:  ["video"]
        }
        assert.deepEqual(
          _.pick(chooser.props(), Object.keys(expectedSimpleProps)),
          expectedSimpleProps
        )
      })

      it("passes upload handler to DropBoxChooser", () => {
        sandbox.stub(CollectionDetailPage.prototype, "handleUpload")
        const chooser = renderUploadFrob().find("DropboxChooser")
        sinon.assert.notCalled(CollectionDetailPage.prototype.handleUpload)
        chooser.prop("success")()
        sinon.assert.called(CollectionDetailPage.prototype.handleUpload)
      })
    })

    describe("handleUpload", () => {
      let chosenFiles

      beforeEach(() => {
        sandbox.stub().returns(Promise.resolve())
        sandbox.stub(actions.uploadVideo, "post")
        sandbox.stub(actions.collections, "get")
        chosenFiles = [...Array(3).keys()].map(i => ({ id: i }))
        page = new CollectionDetailPage(props)
      })

      it("dispatches upload action", async () => {
        sinon.assert.notCalled(actions.uploadVideo.post)
        await page.handleUpload(chosenFiles)
        // $FlowFixMe: collection won't be null.
        const expectedArgs = [page.props.collection.key, chosenFiles]
        sinon.assert.calledWith(actions.uploadVideo.post, ...expectedArgs)
      })

      it("dispatches collections.get action to refresh collection", async () => {
        sinon.assert.notCalled(actions.uploadVideo.post)
        await page.handleUpload(chosenFiles)
        // $FlowFixMe: won't be null
        const expectedArgs = [page.props.collection.key]
        sinon.assert.calledWith(actions.collections.get, ...expectedArgs)
      })
    })

    describe("renderDescription", () => {
      // $FlowFixMe: defaults are ok.
      const renderDescription = ({extraProps = {}, description = ""} = {}) => {
        page = new CollectionDetailPage({ ...props, ...extraProps })
        return shallow(<div>{page.renderDescription(description)}</div>)
      }

      it("renders description text when description is not empty", () => {
        const description = "someDescription"
        const rendered = renderDescription({ description }).childAt(0)
        assert.equal(rendered.text(), description)
        assert.isTrue(rendered.hasClass("description"))
      })

      it("is null when description is empty", () => {
        const emptyDescriptions = ["", null, undefined]
        for (const description of emptyDescriptions) {
          assert.isFalse(
            renderDescription({ description })
              .find(".description")
              .exists()
          )
        }
      })
    })

    describe("renderVideos", () => {
      // $FlowFixMe: defaults are ok.
      const renderVideos = ({extraProps = {}, videos = [], isAdmin = true} = {}) => {
        page = new CollectionDetailPage({ ...props, ...extraProps })
        // $FlowFixMe: isAdmin is ok.
        return shallow(<div>{page.renderVideos(videos, isAdmin)}</div>)
      }

      it("renders 'no videos' message", () => {
        assert.isTrue(
          renderVideos({ videos: [] })
            .find(".no-videos")
            .exists()
        )
      })

      describe("when there are videos", () => {
        const videos = makeCollection().videos
        const isAdmin = "someIsAdminValue"

        it("renders VideoList with expected basic props", () => {
          const videoList = renderVideos({ videos, isAdmin }).find("VideoList")
          const expectedBasicProps = {
            className: "videos",
            videos,
            commonUi:  page.props.commonUi,
            isAdmin
          }
          assert.deepEqual(
            _.pick(videoList.props(), Object.keys(expectedBasicProps)),
            expectedBasicProps
          )
        })

        describe("VideoList function props", () => {
          const methodNames = [
            "showDeleteVideoDialog",
            "showEditVideoDialog",
            "showShareVideoDialog",
            "showVideoMenu",
            "hideVideoMenu",
            "isVideoMenuOpen"
          ]
          _.forEach(methodNames, methodName => {
            it(`it passes bound ${methodName} to VideoList`, () => {
              sandbox.stub(CollectionDetailPage.prototype, methodName)
              const videoList = renderVideos({ videos, isAdmin }).find(
                "VideoList"
              )
              // $FlowFixMe: ignore index access
              sinon.assert.notCalled(CollectionDetailPage.prototype[methodName])
              videoList.prop(methodName)()
              // $FlowFixMe: ignore index access
              sinon.assert.called(CollectionDetailPage.prototype[methodName])
            })
          })
        })
      })
    })

    describe("showVideoDialog methods", () => {
      describe("showVideoDialog", () => {
        const dialogName = "someDialogName"
        const videoKey = "someVideoKey"

        // Ideally we would stub collectionUiActions.setSelectedVideoKey
        // to decouple this test from the internal logic of collectionUiActions,
        // but because of the way that actions/collectionUiActions.js defines
        // exports (as of 2018-05-10) that's not possible.
        // So we just leave it unstubbed, since it makes no api calls and has
        // no side-effects.
        // dorska, 2018-05-10.

        // $FlowFixMe: defaults are ok.
        const showVideoDialog = ({extraProps = {}, dialogName = "", videoKey = ""} = {}) => {
          // $FlowFixMe: Constructor call is intentional.
          page = new CollectionDetailPage({ ...props, ...extraProps })
          page.showVideoDialog(dialogName, videoKey)
        }

        it("dispatches setSelectedVideoKey action", () => {
          showVideoDialog({ dialogName, videoKey })
          const expectedArgs = [
            collectionUiActions.setSelectedVideoKey(videoKey)
          ]
          sinon.assert.calledWith(page.props.dispatch, ...expectedArgs)
        })

        it("calls props.showDialog", () => {
          showVideoDialog({ dialogName, videoKey })
          sinon.assert.called(page.props.showDialog)
        })
      })

      describe("proxying dialog methods", () => {
        beforeEach(() => {
          sandbox.stub(CollectionDetailPage.prototype, "showVideoDialog")
        })

        const methodNamesToDialogNames = {
          showEditVideoDialog:   DIALOGS.EDIT_VIDEO,
          showShareVideoDialog:  DIALOGS.SHARE_VIDEO,
          showDeleteVideoDialog: DIALOGS.DELETE_VIDEO
        }
        _.forEach(methodNamesToDialogNames, (dialogName, methodName) => {
          it("proxies to showVideoDialog", () => {
            const videoKey = "someVideoKey"
            // $FlowFixMe: Constructor call is intentional.
            const page = new CollectionDetailPage(props)
            sinon.assert.notCalled(page.showVideoDialog)
            page[methodName](videoKey)
            sinon.assert.calledWith(page.showVideoDialog, dialogName, videoKey)
          })
        })
      })
    })

    describe("videoMenu methods", () => {
      // Ditto comment above re: stubbing actions here.
      const showHideItems = ["show", "hide"]
      _.forEach(showHideItems, showHide => {
        const methodName = `${showHide}VideoMenu`
        it(methodName, () => {
          const videoKey = "someVideoKey"
          // $FlowFixMe: Constructor call is intentional.
          const page = new CollectionDetailPage(props)
          sinon.assert.notCalled(page.props.dispatch)
          page[methodName](videoKey)
          sinon.assert.calledWith(
            page.props.dispatch,
            collectionUiActions.setSelectedVideoKey(videoKey)
          )
          sinon.assert.calledWith(
            page.props.dispatch,
            commonUiActions[`${showHide}Menu`](videoKey)
          )
        })
      })

      it("isVideoMenuOpen selects from commonUi", () => {
        const videoKey = "someVideoKey"
        const expectedVisibilityValue = "someVisibilityValue"
        const page = new CollectionDetailPage({
          ...props,
          commonUi: Object.assign({}, props.commonUi, {
            menuVisibility: {
              [videoKey]: expectedVisibilityValue
            }
          })
        })
        assert.equal(page.isVideoMenuOpen(videoKey), expectedVisibilityValue)
      })
    })
  })
})
