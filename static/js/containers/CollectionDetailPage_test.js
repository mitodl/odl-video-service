// @flow
/* global SETTINGS: false */
import React from "react"
import _ from "lodash"
import sinon from "sinon"
import { assert } from "chai"
import { screen, fireEvent, waitFor, within } from "@testing-library/react"
import configureTestStore from "redux-asserts"
import DropboxChooser from "react-dropbox-chooser"

import { mapStateToProps, CollectionDetailPage } from "./CollectionDetailPage"
import Menu from "../components/material/Menu"
import { actions } from "../actions"
import * as api from "../lib/api"
import * as collectionUiActions from "../actions/collectionUi"
import * as commonUiActions from "../actions/commonUi"
import rootReducer from "../reducers"
import { INITIAL_UI_STATE } from "../reducers/commonUi"
import { makeCollection } from "../factories/collection"
import { DIALOGS } from "../constants"
import { shouldIf } from "../lib/test_utils"
import renderWithProviders from "../testUtils/renderWithProviders"

describe("CollectionDetailPage", () => {
  let sandbox

  beforeEach(() => {
    sandbox = sinon.createSandbox()
  })

  afterEach(() => {
    sandbox.restore()
    // window.Dropbox is a real global that global_init.js's
    // resetTestEnvironment does not clear, and lib/video.saveToDropbox calls
    // window.Dropbox.save(...) -- leaking a `{ choose }`-only stub into a
    // later test file would be a cross-file landmine.
    delete window.Dropbox
  })

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
        {
          opts:     { loaded: true, data: { key: "somedata" } },
          expected: { key: "somedata" }
        },
        { opts: { loaded: false, data: undefined }, expected: null },
        { opts: { loaded: false, data: {} }, expected: null }
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
          assert.deepEqual(actualProps.collection, testDef.expected)
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
          expected: true // We keep the data regardless of the loaded state now.
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
    ;[
      [true, true, true],
      [false, true, true],
      [true, false, true],
      [false, false, false]
    ].forEach(([isAppAdmin, isEdxCourseAdmin, expAdminProp]) => {
      it(`${shouldIf(
        expAdminProp
      )} set isEdxCourseAdmin=true for the collection edit form
        if is_app_admin=${isAppAdmin.toString()}, is_edx_course_admin=${isEdxCourseAdmin.toString()}`, () => {
        SETTINGS.is_app_admin = isAppAdmin
        SETTINGS.is_edx_course_admin = isEdxCourseAdmin
        const actualProps = mapStateToProps(state, ownProps)
        assert.equal(
          actualProps.dialogProps[DIALOGS.COLLECTION_FORM].isEdxCourseAdmin,
          expAdminProp
        )
      })
    })
  })

  describe("Component", () => {
    let collection, video, props, store

    beforeEach(() => {
      collection = makeCollection()
      video = collection.videos[0]
      props = {
        dispatch:          sandbox.stub(),
        collection,
        collectionError:   undefined,
        collectionKey:     collection.key,
        isCollectionAdmin: false,
        needsUpdate:       false,
        // A full mount reaches CollectionDetailPage.isVideoMenuOpen, which
        // VideoList.renderVideoCard calls during render and which reads
        // commonUi.menuVisibility[videoKey]. The pre-conversion `commonUi: {}`
        // fixture only survived because `shallow` never rendered VideoList.
        commonUi:          { ...INITIAL_UI_STATE },
        showDialog:        sandbox.stub()
      }
      // material/Drawer's componentDidMount dispatches
      // actions.collectionsList.get() whenever collectionsList is neither
      // processing nor loaded; pre-seeding it keeps every render below
      // synchronous and free of api stubs. The key must be spelled exactly as
      // the endpoint name in reducers/collections.js -- any key the combined
      // reducer does not know makes redux console.error an "Unexpected key"
      // warning to stderr, which the frozen js_test.sh allowlist rejects.
      store = configureTestStore(rootReducer, {
        collectionsList: {
          processing: false,
          loaded:     true,
          data:       { results: [] }
        }
      })
    })

    // props.dispatch stays a plain stub, so the page's own dispatches are
    // asserted against it; the store's dispatch only ever serves
    // WithDrawer/Drawer. With needsUpdate false and no collectionError,
    // componentDidMount/componentDidUpdate dispatch nothing, so the
    // `notCalled(props.dispatch)` preconditions below still hold after mount.
    const renderPage = (extraProps = {}) =>
      renderWithProviders(
        <CollectionDetailPage {...{ ...props, ...extraProps }} />,
        { store }
      )

    // The admin tools and the admin video-card menu items only render when
    // isCollectionAdmin is true.
    const renderAdmin = (extraProps = {}) =>
      renderPage({ isCollectionAdmin: true, ...extraProps })

    // A one-video collection keeps `more_vert`, the menu-item labels and the
    // Menu render spy's lastCall unambiguous (the factory makes two videos,
    // i.e. two menus with duplicate labels).
    const renderOneVideoAdmin = (extraProps = {}) =>
      renderAdmin({
        collection: { ...collection, videos: [video] },
        ...extraProps
      })

    // Menu's <ul role="menu"> carries a hardcoded aria-hidden="true"
    // (Menu.js:57-59) that MDCMenu never toggles under jsdom, so menu items
    // need RTL's `hidden: true` escape hatch -- same as VideoCard_test.js.
    const menuItems = () => screen.getAllByRole("menuitem", { hidden: true })
    const menuItem = label => menuItems().find(el => el.textContent === label)

    // Both frob buttons wrap an icon/alt text ("sync Sync Videos with edX",
    // "Dropbox Icon Add Videos from Dropbox"), so the accessible name has to
    // be matched with a regex, never an exact string.
    const syncButton = () =>
      screen.getByRole("button", { name: /Sync Videos with edX/ })
    const dropboxButton = () =>
      screen.getByRole("button", { name: /Add Videos from Dropbox/ })

    describe("render", () => {
      it("renders drawer", () => {
        renderPage()
        // Both of these are real user-visible chrome that only exists inside
        // WithDrawer: OVSToolbar's title link and material/Drawer's header
        // link.
        assert.isNotNull(screen.getByText("ODL Video Services"))
        assert.isNotNull(screen.getByText("My Collections"))
      })

      describe("when there is an error", () => {
        it("renders error", () => {
          const { container, unmount } = renderPage({
            collectionError: "someError"
          })
          // "someError" has no `.detail`, so renderError falls through to
          // <ErrorMessages.UnableToLoadData/>.
          assert.isNotNull(
            within(container).getByText(
              /unable to load the data necessary to process your request/
            )
          )
          assert.isNull(container.querySelector(".centered-content"))
          unmount()

          // The `error.detail` branch, which the marker-stub version of this
          // test could never see.
          const detailed = renderPage({
            collectionError: { detail: "someDetail" }
          })
          assert.equal(
            detailed.container.querySelector(".odl-error-message").textContent,
            "Error: someDetail"
          )
          assert.isNull(detailed.container.querySelector(".centered-content"))
        })
      })

      describe("when there is no error", () => {
        it("renders body", () => {
          const { container } = renderPage()
          assert.isNotNull(container.querySelector(".centered-content"))
          assert.equal(
            screen.getByRole("heading", { level: 1 }).textContent,
            `${collection.title} (2)`
          )
          assert.isNull(container.querySelector(".odl-error-message"))
        })
      })
    })

    describe("renderBody", () => {
      it("renders tools", () => {
        const { container } = renderPage()
        assert.isNotNull(
          container.querySelector(".centered-content header .tools")
        )
      })

      it("renders description", () => {
        const { container } = renderPage()
        assert.equal(
          container.querySelector(".description").textContent,
          collection.description
        )
      })

      it("renders videos", () => {
        const { container } = renderPage()
        assert.isNotNull(container.querySelector(".video-list.videos"))
        assert.equal(container.querySelectorAll(".video-card").length, 2)
      })
    })

    describe("renderTools", () => {
      it("has tools class", () => {
        const { container } = renderPage()
        assert.isNotNull(container.querySelector("header .tools"))
      })

      it("renders admin tools if isAdmin", () => {
        const { container } = renderAdmin()
        assert.isNotNull(
          within(container.querySelector(".tools")).getByText("settings")
        )
      })

      it("does not render admin tools if not isAdmin", () => {
        const { container } = renderPage({ isCollectionAdmin: false })
        // `{isAdmin && this.renderAdminTools()}` renders nothing for false.
        assert.equal(container.querySelector(".tools").childElementCount, 0)
      })
    })

    describe("renderAdminTools", () => {
      let tools

      beforeEach(() => {
        const { container } = renderAdmin()
        tools = container.querySelector(".tools")
      })

      it("renders settings frob", () => {
        assert.isNotNull(tools.querySelector("#edit-collection-button"))
      })

      it("renders sync with edX frob", () => {
        // makeCollection()'s edx_course_id is truthy (casual.word).
        assert.isNotNull(
          within(tools).getByRole("button", { name: /Sync Videos with edX/ })
        )
      })

      it("renders upload frob", () => {
        assert.isNotNull(
          within(tools).getByRole("button", {
            name: /Add Videos from Dropbox/
          })
        )
      })
    })

    describe("renderSettingsFrob", () => {
      it("has settings icon", () => {
        const { container } = renderAdmin()
        const frob = container.querySelector("#edit-collection-button")
        assert.isNotNull(frob)
        assert.equal(
          frob.querySelector(".material-icons").textContent,
          "settings"
        )
      })

      it("triggers showEditCollectionDialog when clicked", () => {
        // The prototype stub is installed before the render because
        // renderSettingsFrob does the `.bind(this)` at render time.
        //
        // Asserting the real dispatch instead is not possible:
        // collectionUiActions.showEditCollectionDialog returns a thunk -- a
        // fresh function per call -- so calledWith could never deep-equal it.
        const stub = sandbox.stub(
          CollectionDetailPage.prototype,
          "showEditCollectionDialog"
        )
        renderAdmin()
        sinon.assert.notCalled(stub)
        // The frob's <a> has no href, so this click cannot make jsdom log a
        // "Not implemented: navigation" error to stderr. The click bubbles
        // from the <i> to the <a>'s React onClick.
        fireEvent.click(screen.getByText("settings"))
        sinon.assert.called(stub)
      })
    })

    describe("renderUploadFrob", () => {
      it("renders DropBoxChooser with expected simple props", () => {
        SETTINGS.dropbox_key = "someAppKey"
        const chooseStub = sandbox.stub()
        window.Dropbox = { choose: chooseStub }
        // appKey is not reachable through window.Dropbox.choose -- it is only
        // used for the <script> react-dropbox-chooser injects in
        // componentDidMount, behind a module-level `scriptLoadingStarted` flag
        // that an earlier test file has already consumed (and VideoSaverScript
        // injects a tag with the same id and data-app-key), so asserting the
        // #dropboxjs tag would be an order-dependent false positive. Capture
        // the props the real rendered component received instead.
        const chooserRenderSpy = sandbox.spy(DropboxChooser.prototype, "render")
        // videos: [] leaves the upload frob's chooser as the only
        // DropboxChooser in the tree -- VideoCards render their own hidden
        // ones, which would otherwise win lastCall.
        renderAdmin({ collection: { ...collection, videos: [] } })
        assert.equal(
          chooserRenderSpy.lastCall.thisValue.props.appKey,
          "someAppKey"
        )

        fireEvent.click(dropboxButton())
        assert.deepEqual(
          _.pick(chooseStub.firstCall.args[0], [
            "linkType",
            "multiselect",
            "extensions"
          ]),
          { linkType: "preview", multiselect: true, extensions: ["video"] }
        )
      })

      it("passes upload handler to DropBoxChooser", () => {
        const chosenFiles = [{ id: 0 }]
        window.Dropbox = { choose: opts => opts.success(chosenFiles) }
        const stub = sandbox.stub(
          CollectionDetailPage.prototype,
          "handleUpload"
        )
        renderAdmin({ collection: { ...collection, videos: [] } })
        sinon.assert.notCalled(stub)
        fireEvent.click(dropboxButton())
        // Stronger than the old `chooser.prop("success")()`: the handler is
        // reached through the chooser's real success callback, with the real
        // chosen-file payload.
        sinon.assert.calledWith(stub, chosenFiles)
      })
    })

    describe("handleUpload", () => {
      let chosenFiles

      beforeEach(() => {
        sandbox.stub(actions.uploadVideo, "post")
        sandbox.stub(actions.collections, "get")
        chosenFiles = [...Array(3).keys()].map(i => ({ id: i }))
        window.Dropbox = { choose: opts => opts.success(chosenFiles) }
        renderAdmin({ collection: { ...collection, videos: [] } })
      })

      it("dispatches upload action", () => {
        sinon.assert.notCalled(actions.uploadVideo.post)
        fireEvent.click(dropboxButton())
        // Synchronous: it happens before handleUpload's first await.
        sinon.assert.calledWith(
          actions.uploadVideo.post,
          collection.key,
          chosenFiles
        )
      })

      it("dispatches collections.get action to refresh collection", async () => {
        fireEvent.click(dropboxButton())
        // handleUpload awaits dispatch(uploadVideo.post(...)) first, so the
        // refresh lands a microtask later than the click.
        await waitFor(() =>
          sinon.assert.calledWith(actions.collections.get, collection.key)
        )
      })
    })

    describe("renderDescription", () => {
      it("renders a plain-text description as text, keeping its line breaks", () => {
        /*
         * What the format on the record says, not what the value looks like.
         * Injecting a legacy plain-text description as markup is what truncates
         * it: `<b to a` is read as an unterminated tag and everything after it
         * disappears.
         */
        const { container } = renderPage({
          collection: {
            ...collection,
            description:        "Compare <b to a.\nSecond line.",
            description_format: "text"
          }
        })
        const description = container.querySelector("div.description")
        assert.isNotNull(description)
        assert.equal(description.textContent, "Compare <b to a.\nSecond line.")
        assert.lengthOf(description.querySelectorAll("b"), 0)
        assert.isTrue(
          description.classList.contains("description-plain-text"),
          "pre-wrap is what keeps the author's line breaks visible"
        )
      })

      it("renders a rich-text description as markup", () => {
        // Sanitized server-side on write (ui/html.py), so it is injected. A div,
        // not a p: the markup can contain block elements, which a p cannot hold.
        const { container } = renderPage({
          collection: {
            ...collection,
            description:
              "<p>a <strong>seminar</strong></p><ul><li>one</li></ul>",
            description_format: "html"
          }
        })
        const description = container.querySelector("div.description")
        assert.isNotNull(description)
        assert.equal(description.querySelectorAll("strong").length, 1)
        assert.equal(description.querySelectorAll("ul > li").length, 1)
      })
      ;[
        ["", "an empty string"],
        [null, "null"],
        [undefined, "undefined"]
      ].forEach(([description, label]) => {
        // The pre-conversion version looped over these three inside a single
        // `it`; one test per case reports which value regressed.
        it(`renders no description when it is ${label}`, () => {
          const { container } = renderPage({
            collection: { ...collection, description }
          })
          assert.isNull(container.querySelector(".description"))
        })
      })
    })

    describe("renderVideos", () => {
      it("renders 'no videos' message", () => {
        const { container } = renderAdmin({
          collection: { ...collection, videos: [] }
        })
        assert.isNotNull(container.querySelector(".no-videos"))
        assert.isNotNull(screen.getByText(/There are no videos yet/))
      })

      it("renders 'no videos' message for anonymous", () => {
        renderPage({
          collection:        { ...collection, videos: [] },
          isCollectionAdmin: false
        })
        // Exact accessible name, so the drawer's "Not logged in" link cannot
        // match. Deliberately not clicked: firing a click on a real <a href>
        // makes jsdom print "Error: Not implemented: navigation" to stderr,
        // which the frozen js_test.sh allowlist rejects.
        const link = screen.getByRole("link", { name: "login" })
        assert.equal(
          link.getAttribute("href"),
          `/login/?next=/collections/${collection.key}`
        )
      })

      describe("when there are videos", () => {
        it("renders VideoList with expected basic props", () => {
          const admin = renderAdmin()
          // className
          assert.isNotNull(admin.container.querySelector(".video-list.videos"))
          // videos, in order
          assert.deepEqual(
            Array.from(
              admin.container.querySelectorAll(".video-card-body h2 a")
            ).map(anchor => anchor.textContent),
            collection.videos.map(collectionVideo => collectionVideo.title)
          )
          // isAdmin: admins get the full five-item card menu, everyone else
          // only "Share".
          assert.equal(menuItems().length, 10)
          // The `commonUi` prop VideoList also receives is deliberately not
          // asserted: VideoList never reads it (its prop types do not declare
          // it and neither render nor renderVideoCard touch it), so it has no
          // user-visible or stubbable consequence. Dropped here rather than
          // deleted from the component -- that would be a production change.
          admin.unmount()

          renderPage({ isCollectionAdmin: false })
          assert.equal(menuItems().length, 2)
        })

        describe("VideoList function props", () => {
          // Every `.bind(this)` in renderVideos happens during render, so each
          // prototype stub below must be installed before the render.
          it("it passes bound showDeleteVideoDialog to VideoList", () => {
            const stub = sandbox.stub(
              CollectionDetailPage.prototype,
              "showDeleteVideoDialog"
            )
            renderOneVideoAdmin()
            sinon.assert.notCalled(stub)
            fireEvent.click(menuItem("Delete"))
            sinon.assert.called(stub)
          })

          it("it passes bound showEditVideoDialog to VideoList", () => {
            const stub = sandbox.stub(
              CollectionDetailPage.prototype,
              "showEditVideoDialog"
            )
            renderOneVideoAdmin()
            sinon.assert.notCalled(stub)
            fireEvent.click(menuItem("Edit"))
            sinon.assert.called(stub)
          })

          it("it passes bound showShareVideoDialog to VideoList", () => {
            const stub = sandbox.stub(
              CollectionDetailPage.prototype,
              "showShareVideoDialog"
            )
            renderOneVideoAdmin()
            sinon.assert.notCalled(stub)
            fireEvent.click(menuItem("Share"))
            sinon.assert.called(stub)
          })

          it("it passes bound showVideoMenu to VideoList", () => {
            const stub = sandbox.stub(
              CollectionDetailPage.prototype,
              "showVideoMenu"
            )
            renderOneVideoAdmin()
            sinon.assert.notCalled(stub)
            // Menu.js:47-49 wires showMenu directly onto the "more_vert" <a>,
            // which has no href.
            fireEvent.click(screen.getByText("more_vert"))
            sinon.assert.called(stub)
          })

          it("it passes bound hideVideoMenu to VideoList", () => {
            const stub = sandbox.stub(
              CollectionDetailPage.prototype,
              "hideVideoMenu"
            )
            // Documented exception, the same one VideoCard_test.js records:
            // material/Menu wires closeMenu only to MDCMenu's own
            // "MDCMenu:cancel"/"MDCMenu:selected" events (Menu.js:22-25), and
            // those never fire under jsdom -- MDC's menu-surface foundation
            // needs real layout metrics. So instead of dropping the assertion,
            // grab the actual closeMenu prop the real rendered <Menu>
            // received and invoke it. This still fails if the page or
            // VideoList stop wiring hideVideoMenu through; it just cannot
            // travel through MDC's own event dispatch in this environment.
            const menuRenderSpy = sandbox.spy(Menu.prototype, "render")
            renderOneVideoAdmin()
            sinon.assert.notCalled(stub)
            menuRenderSpy.lastCall.thisValue.props.closeMenu()
            sinon.assert.called(stub)
          })

          it("it passes bound isVideoMenuOpen to VideoList", () => {
            const stub = sandbox.stub(
              CollectionDetailPage.prototype,
              "isVideoMenuOpen"
            )
            renderOneVideoAdmin()
            // VideoList.renderVideoCard calls it during render, so no event is
            // needed -- and it is called with the video's own key.
            sinon.assert.calledWith(stub, video.key)
          })
        })
      })
    })

    describe("showVideoDialog methods", () => {
      describe("showVideoDialog", () => {
        // collectionUiActions.setSelectedVideoKey is a plain createAction, so
        // the dispatched action deep-equals a freshly built one. (Contrast
        // showEditCollectionDialog, which returns a thunk -- see
        // renderSettingsFrob above.)

        it("dispatches setSelectedVideoKey action", () => {
          renderOneVideoAdmin()
          sinon.assert.notCalled(props.dispatch)
          fireEvent.click(menuItem("Share"))
          sinon.assert.calledWith(
            props.dispatch,
            collectionUiActions.setSelectedVideoKey(video.key)
          )
        })

        it("calls props.showDialog", () => {
          renderOneVideoAdmin()
          sinon.assert.notCalled(props.showDialog)
          fireEvent.click(menuItem("Share"))
          sinon.assert.calledWith(props.showDialog, DIALOGS.SHARE_VIDEO)
        })
      })

      describe("proxying dialog methods", () => {
        const methodCases = [
          ["showEditVideoDialog", DIALOGS.EDIT_VIDEO, "Edit"],
          ["showShareVideoDialog", DIALOGS.SHARE_VIDEO, "Share"],
          ["showDeleteVideoDialog", DIALOGS.DELETE_VIDEO, "Delete"]
        ]
        _.forEach(methodCases, ([methodName, dialogName, label]) => {
          it(`${methodName} proxies to showVideoDialog with ${dialogName}`, () => {
            renderOneVideoAdmin()
            fireEvent.click(menuItem(label))
            sinon.assert.calledWith(props.showDialog, dialogName)
            sinon.assert.calledWith(
              props.dispatch,
              collectionUiActions.setSelectedVideoKey(video.key)
            )
          })
        })
      })
    })

    describe("videoMenu methods", () => {
      it("showVideoMenu", () => {
        renderOneVideoAdmin()
        sinon.assert.notCalled(props.dispatch)
        fireEvent.click(screen.getByText("more_vert"))
        sinon.assert.calledWith(
          props.dispatch,
          collectionUiActions.setSelectedVideoKey(video.key)
        )
        sinon.assert.calledWith(
          props.dispatch,
          commonUiActions.showMenu(video.key)
        )
      })

      it("hideVideoMenu", () => {
        // Same MDC limitation as the hideVideoMenu VideoList-prop test above:
        // closeMenu has no jsdom-reachable DOM trigger, so invoke the real
        // prop the real rendered <Menu> received.
        const menuRenderSpy = sandbox.spy(Menu.prototype, "render")
        renderOneVideoAdmin()
        sinon.assert.notCalled(props.dispatch)
        menuRenderSpy.lastCall.thisValue.props.closeMenu()
        sinon.assert.calledWith(
          props.dispatch,
          collectionUiActions.setSelectedVideoKey(video.key)
        )
        sinon.assert.calledWith(
          props.dispatch,
          commonUiActions.hideMenu(video.key)
        )
      })

      it("isVideoMenuOpen selects from commonUi", () => {
        const expectedVisibilityValue = "someVisibilityValue"
        const menuRenderSpy = sandbox.spy(Menu.prototype, "render")
        renderOneVideoAdmin({
          commonUi: {
            ...INITIAL_UI_STATE,
            menuVisibility: { [video.key]: expectedVisibilityValue }
          }
        })
        // Asserts the whole chain, page -> VideoList -> VideoCard -> Menu,
        // rather than just the accessor. An MDC open-class assertion would be
        // vacuous here: Menu applies `open` only in componentDidUpdate, and
        // @material/menu gates the class behind requestAnimationFrame, which
        // global_init.js stubs to a no-op.
        assert.equal(
          menuRenderSpy.lastCall.thisValue.props.open,
          expectedVisibilityValue
        )
      })
    })

    describe("renderSyncWithEdXFrob", () => {
      const collectionWithEdX = () => ({
        ...collection,
        edx_course_id: "course-v1:edX+DemoX+Demo_Course"
      })

      it("renders sync with edX button when collection has edx_course_id", () => {
        renderAdmin({ collection: collectionWithEdX() })
        assert.isTrue(syncButton().classList.contains("sync-edx-btn"))
      })

      it("does not render sync button when collection has no edx_course_id", () => {
        const { container } = renderAdmin({
          collection: { ...collection, edx_course_id: null }
        })
        assert.isNull(container.querySelector(".sync-edx-btn"))
      })

      it("does not render sync button when collection is null", () => {
        const { container } = renderAdmin({ collection: null })
        assert.isNull(container.querySelector(".sync-edx-btn"))
        // Weakened, and vacuous by unreachability: render() returns null when
        // there is neither a collection nor an error, so nothing renders at
        // all and renderSyncWithEdXFrob's own `!collection` guard has no DOM
        // path -- it is defensive-only. The count assertion below at least
        // pins the real observable behaviour of a null collection.
        assert.equal(container.children.length, 0)
      })

      it("calls handleSyncWithEdX when clicked", () => {
        // Installed before the render: renderSyncWithEdXFrob binds at render
        // time.
        const stub = sandbox.stub(
          CollectionDetailPage.prototype,
          "handleSyncWithEdX"
        )
        renderAdmin({ collection: collectionWithEdX() })
        sinon.assert.notCalled(stub)
        fireEvent.click(syncButton())
        sinon.assert.called(stub)
      })
    })

    describe("handleSyncWithEdX", () => {
      let syncStub

      beforeEach(() => {
        // handleSyncWithEdX does a lazy `require("../lib/api")` at call time,
        // and babel compiles lib/api.js's `export function` to a writable
        // `exports.*` property, so stubbing the imported namespace is exactly
        // what that require picks up.
        syncStub = sandbox
          .stub(api, "syncCollectionVideosWithEdX")
          .returns(Promise.resolve())
      })

      const renderSyncable = (extraProps = {}) =>
        renderAdmin({
          collection: {
            ...collection,
            edx_course_id: "course-v1:edX+DemoX+Demo_Course"
          },
          ...extraProps
        })

      const expectedToast = (key, content, icon) =>
        actions.toast.addMessage({ message: { key, content, icon } })

      it("prevents default event behavior", () => {
        renderSyncable()
        // fireEvent returns dispatchEvent's boolean, which is false exactly
        // when a cancelable event had preventDefault() called on it. React
        // 15's SyntheticEvent.preventDefault forwards to the native event, so
        // this observes the handler's real e.preventDefault(). Verified
        // empirically on this harness.
        assert.isFalse(fireEvent.click(syncButton()))
      })

      it("makes API call with collection key", () => {
        renderSyncable()
        // Synchronous: the call happens before the handler's first await.
        fireEvent.click(syncButton())
        sinon.assert.calledWith(syncStub, props.collectionKey)
      })

      it("dispatches success toast message when API call succeeds", async () => {
        renderSyncable()
        fireEvent.click(syncButton())
        await waitFor(() =>
          sinon.assert.calledWith(
            props.dispatch,
            expectedToast(
              "scheduled-sync",
              "Videos are being synced with edX. This may take a few minutes.",
              "check"
            )
          )
        )
      })

      it("dispatches error toast message when API call fails", async () => {
        const error = { error: "Custom error message" }
        syncStub.returns(Promise.reject(error))
        renderSyncable()
        fireEvent.click(syncButton())
        await waitFor(() =>
          sinon.assert.calledWith(
            props.dispatch,
            expectedToast("sync-error", error.error, "error")
          )
        )
      })

      it("dispatches generic error message when API call fails without error details", async () => {
        syncStub.returns(Promise.reject({}))
        renderSyncable()
        fireEvent.click(syncButton())
        await waitFor(() =>
          sinon.assert.calledWith(
            props.dispatch,
            expectedToast(
              "sync-error",
              "Failed to sync videos with edX",
              "error"
            )
          )
        )
      })

      it("does not call the API when collectionKey is missing", () => {
        // Weakened: a DOM-triggered handler's return value is unobservable, so
        // the old `assert.isNull(result)` is gone. The observable half -- no
        // API call and no dispatch -- is kept.
        renderSyncable({ collectionKey: null })
        sinon.assert.notCalled(props.dispatch)
        fireEvent.click(syncButton())
        sinon.assert.notCalled(syncStub)
        sinon.assert.notCalled(props.dispatch)
      })
    })

    describe("Owner display", () => {
      it("displays the owner username", () => {
        const { container } = renderPage()
        const ownerElement = container.querySelector(".collection-owner")
        assert.isNotNull(ownerElement)
        assert.equal(
          ownerElement.textContent.trim(),
          `Owner: ${collection.owner_info.username}`
        )
      })
    })
  })
})
