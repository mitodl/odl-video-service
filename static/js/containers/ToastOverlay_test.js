// @flow
import React from "react"
import _ from "lodash"
import { render } from "@testing-library/react"
import { assert } from "chai"
import sinon from "sinon"

import type { ToastMessage as ToastMessageType } from "../flow/toastTypes"
import { ToastOverlay, ToastMessage, mapStateToProps } from "./ToastOverlay"

describe("ToastOverlayTests", () => {
  let sandbox

  beforeEach(() => {
    sandbox = sinon.createSandbox()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const generateMessages = (n?: number = 3): Array<ToastMessageType> => {
    return [...Array(n).keys()].map(i => generateMessage(i))
  }

  const generateMessage = (
    key: string | number = 1,
    extraProps: Object = {}
  ): ToastMessageType => {
    return {
      key,
      content: `${key}:content`,
      ...extraProps
    }
  }

  describe("mapStateToProps", () => {
    it("passes messages", () => {
      const someState = {
        toast: {
          messages: generateMessages()
        },
        someOther: "someOtherStateShard"
      }
      const expectedProps = { messages: someState.toast.messages }
      const actualProps = mapStateToProps(someState)
      assert.deepEqual(actualProps, expectedProps)
    })
  })

  describe("ToastOverlay", () => {
    class DummyMessageComponent extends React.Component<*, void> {
      render() {
        return <div />
      }
    }

    const renderComponent = (extraProps = {}) => {
      const mergedProps = {
        dispatch:         sandbox.stub(),
        messages:         generateMessages(3),
        MessageComponent: DummyMessageComponent,
        ...extraProps
      }
      return render(<ToastOverlay {...mergedProps} />)
    }

    describe("when there are no messages", () => {
      it("renders nothing", () => {
        const { container } = renderComponent({ messages: [] })
        // React 15 leaves a `<!-- react-empty: N -->` comment placeholder in
        // the container when a component renders null, so `firstChild` is
        // never actually `null` here (confirmed via Rule 26 DOM capture --
        // the Enzyme version's `wrapper.html()` was `null`, matching
        // `isEmptyRender()`, but jsdom's real container always keeps that
        // comment node). `children` excludes comment/text nodes, so an empty
        // `children` collection is the accurate "rendered nothing" check.
        assert.lengthOf(container.children, 0)
      })
    })

    describe("when there are messages", () => {
      it("renders messages with MessageComponent in transition group", () => {
        const messages = generateMessages(3)
        // DummyMessageComponent (defined above, test-owned) renders an empty
        // `<div />` with no distinguishing content, so nothing in the
        // rendered DOM can tell one message's card apart from another --
        // confirmed empirically via Rule 26 DOM capture of the Enzyme
        // version, which showed three indistinguishable
        // `.toast-transition-appear` divs. Spying on the dummy's own
        // `render` and reading `thisValue.props` is the same technique
        // VideoCard_test.js uses for Menu.prototype.render.
        const messageRenderSpy = sandbox.spy(
          DummyMessageComponent.prototype,
          "render"
        )
        const { container } = renderComponent({ messages })
        // CSSTransition's `appear` transition re-renders each child once
        // more after mount (exited -> "-active"), so each MessageComponent
        // instance is rendered twice, not once -- verified empirically by
        // logging call.thisValue identity across calls. Dedupe by instance
        // identity to get back to "one component per message" before
        // checking count/order/reference-equality, which is what the
        // original Enzyme `.find()` snapshot (read after settling) actually
        // asserted.
        const uniqueCalls = _.uniqBy(
          messageRenderSpy.getCalls(),
          call => call.thisValue
        )
        assert.equal(uniqueCalls.length, messages.length)
        uniqueCalls.forEach((call, i) => {
          assert.equal(call.thisValue.props.message, messages[i])
        })
        // DOM-visible proxy for "wrapped in the transition group": the
        // TransitionGroup renders as a real `.toast-messages` div, present
        // only because messages.length > 0.
        assert.isNotNull(container.querySelector(".toast-messages"))
      })

      it("passes removeMessage to MessageComponent", () => {
        const messages = generateMessages(3)
        const removeMessageStub = sandbox.stub(
          ToastOverlay.prototype,
          "removeMessage"
        )
        const messageRenderSpy = sandbox.spy(
          DummyMessageComponent.prototype,
          "render"
        )
        renderComponent({ messages })
        // Same double-render-per-instance behavior as above; dedupe first.
        const uniqueCalls = _.uniqBy(
          messageRenderSpy.getCalls(),
          call => call.thisValue
        )
        assert.equal(uniqueCalls.length, messages.length)
        uniqueCalls.forEach((call, i) => {
          assert.equal(removeMessageStub.callCount, i)
          call.thisValue.props.removeMessage()
          assert.equal(removeMessageStub.callCount, i + 1)
        })
      })
    })
  })

  describe("ToastMessage", () => {
    const renderComponent = (extraProps = {}) => {
      const mergedProps = {
        message:       generateMessage(),
        removeMessage: sandbox.stub(),
        ...extraProps
      }
      return render(<ToastMessage {...mergedProps} />)
    }

    it("renders the message", () => {
      const message = generateMessage()
      const { container } = renderComponent({ message })
      assert.equal(
        container.querySelector(".message-content").textContent,
        message.content
      )
    })

    describe("icon", () => {
      describe("when icon is present", () => {
        const icon = "someIcon"
        const message = generateMessage(1, { icon })

        it("it renders icon", () => {
          const { container } = renderComponent({ message })
          assert.equal(
            container.querySelector(".message-icon").textContent,
            message.icon
          )
        })
      })

      describe("when icon is absent", () => {
        const message = _.omit(generateMessage(), ["icon"])

        it("it does not render icon", () => {
          const { container } = renderComponent({ message })
          assert.isNull(container.querySelector(".message-icon"))
        })
      })
    })
  })
})
