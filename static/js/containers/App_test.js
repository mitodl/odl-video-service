// @flow
/* global SETTINGS: false */
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { screen } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import configureTestStore from "redux-asserts"

import App from "./App"
import { VideoDetailPage as UnwrappedVideoDetailPage } from "./VideoDetailPage"
import { VideoEmbedPage as UnwrappedVideoEmbedPage } from "./VideoEmbedPage"
import rootReducer from "../reducers"
import renderWithProviders from "../testUtils/renderWithProviders"
import * as api from "../lib/api"
import { makeCollection } from "../factories/collection"

describe("App", () => {
  const renderComponent = (extraProps = {}) => {
    const mergedProps = {
      match: { url: "/" },
      ...extraProps
    }
    const store = configureTestStore(rootReducer, {
      toast: { messages: [{ key: "1", content: "test message" }] }
    })
    return renderWithProviders(
      <MemoryRouter>
        <App {...mergedProps} />
      </MemoryRouter>,
      { store }
    )
  }

  it("has toast message", () => {
    const { container } = renderComponent()
    assert.isNotNull(container.querySelector(".toast-overlay"))
  })

  // App builds each <Route path> from `${match.url}<segment>`, so match.url
  // has to be "/" here to match the six routes below -- the original "has
  // toast message" test above passes match: {url: "/"} too, but every one of
  // its six <Route>s resolves to null against a MemoryRouter defaulted to
  // "/", so nothing but <ToastOverlay/> was ever exercised. These tests
  // navigate to each route's actual path instead, so App.js's route wiring
  // -- four of whose six routes this branch (Task 4, react-redux 5 -> 8)
  // switched from `component={ConnectedPage}` to
  // `render={routeProps => <ConnectedPage {...routeProps} />}` -- is
  // actually proven, not merely rendered past.
  describe("routing", () => {
    let sandbox

    beforeEach(() => {
      sandbox = sinon.createSandbox()
      // Every route below mounts WithDrawer, whose child Drawer dispatches
      // actions.collectionsList.get() (-> api.getCollections()) on mount
      // regardless of which route matched. A promise that never resolves
      // keeps that dispatch harmlessly pending (FETCH_PROCESSING only) for
      // every test in this block, with no api stub duplicated per test.
      sandbox.stub(api, "getCollections").returns(new Promise(() => {}))
      // CollectionListPage and CollectionDetailPage are both wrapped in
      // withDialogs, which always mounts CollectionFormDialog (visibility is
      // CSS-only, per components/dialogs/hoc.js -- `open` is just a prop).
      // Its componentDidMount fetches potential owners whenever a
      // collectionKey prop reaches it, which the collections/:collectionKey/
      // route below does supply (real fetch would fail: fetch() has no
      // absolute base URL under jsdom).
      sandbox
        .stub(api, "getPotentialCollectionOwners")
        .returns(new Promise(() => {}))
    })

    afterEach(() => {
      sandbox.restore()
    })

    const renderAppAt = (path, preloadedState = {}) => {
      const store = configureTestStore(rootReducer, preloadedState)
      return renderWithProviders(
        <MemoryRouter initialEntries={[path]}>
          <App match={{ url: "/" }} />
        </MemoryRouter>,
        { store }
      )
    }

    it("routes /collections/ to CollectionListPage", () => {
      renderAppAt("/collections/")
      // WithDrawer's own nav also links to "My Collections", so this has to
      // be scoped to the page's own <h1> to stay unambiguous.
      assert.isNotNull(
        screen.getByRole("heading", { level: 1, name: "My Collections" })
      )
    })

    it("routes /collections/:collectionKey/ to CollectionDetailPage, with the URL param reaching it via the route's own props", () => {
      // CollectionDetailPage's connected mapStateToProps reads
      // ownProps.match.params.collectionKey directly (CollectionDetailPage.js
      // ~L379), so this route only renders real content -- instead of
      // silently staying null -- when react-router's match/location/history
      // are actually forwarded. Pre-loading a matching, already-loaded
      // `collections` slice lets the page render its real body synchronously
      // (no async fetch to await), which is exactly what proves the wiring:
      // if `render`'s routeProps were ever dropped, `match` would be
      // undefined and mapStateToProps would throw immediately (see the
      // load-bearing experiment in final-fix-wave-report.md).
      const collection = { ...makeCollection(), videos: [] }
      renderAppAt(`/collections/${collection.key}/`, {
        collections: { processing: false, loaded: true, data: collection }
      })
      assert.isNotNull(screen.getByText(`${collection.title} (0)`))
    })

    it("routes /help/ to HelpPage", () => {
      renderAppAt("/help/")
      assert.isNotNull(screen.getByText("General Questions"))
    })

    it("routes /terms/ to TermsPage", () => {
      renderAppAt("/terms/")
      assert.isNotNull(screen.getByText("Terms of Service"))
    })

    // videos/:videoKey/ and embeds/:videoKey/ use `component={boundMethod}`,
    // not the `render` prop -- these are the two routes Task 4 did NOT have
    // to change (bound class-property arrow functions are real
    // typeof "function", so react-router 4's `component: PropTypes.func`
    // check never tripped on them). Both target pages mount video.js and
    // fire GA calls; VideoDetailPage_test.js and VideoEmbedPage_test.js
    // already cover that behavior exhaustively with the stubs it requires
    // (videojs, dropbox, api). Duplicating that here would only re-test
    // those pages, not App's routing, so render() and componentDidMount()
    // are replaced with cheap stand-ins and this only proves what's actually
    // in scope: that the route resolves to the right page component, with
    // the SETTINGS-derived props and the spread routeProps both reaching it.
    describe("bound-method routes", () => {
      it("routes /videos/:videoKey/ to VideoDetailPage", () => {
        let captured
        sandbox.stub(UnwrappedVideoDetailPage.prototype, "componentDidMount")
        sandbox
          .stub(UnwrappedVideoDetailPage.prototype, "render")
          .callsFake(function() {
            captured = this.props
            return <div data-testid="video-detail-marker" />
          })

        renderAppAt(`/videos/${SETTINGS.videoKey}/`)

        assert.isNotNull(screen.getByTestId("video-detail-marker"))
        assert.equal(captured.videoKey, SETTINGS.videoKey)
        assert.equal(captured.isAdmin, !!SETTINGS.is_video_admin)
        assert.equal(captured.match.params.videoKey, SETTINGS.videoKey)
      })

      it("routes /embeds/:videoKey/ to VideoEmbedPage", () => {
        let captured
        sandbox.stub(UnwrappedVideoEmbedPage.prototype, "componentDidMount")
        sandbox
          .stub(UnwrappedVideoEmbedPage.prototype, "render")
          .callsFake(function() {
            captured = this.props
            return <div data-testid="video-embed-marker" />
          })

        renderAppAt(`/embeds/${SETTINGS.videoKey}/`)

        assert.isNotNull(screen.getByTestId("video-embed-marker"))
        assert.equal(captured.video, SETTINGS.video)
        assert.equal(captured.match.params.videoKey, SETTINGS.videoKey)
      })
    })
  })
})
