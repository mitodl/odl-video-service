// @flow
import React from "react"
import _ from "lodash"
import { mount } from "enzyme"
import { assert } from "chai"
import sinon from "sinon"

import type { ToastMessage as ToastMessageType } from "../flow/toastTypes"
import { ToastOverlay, ToastMessage, mapStateToProps } from "./ToastOverlay"

describe("ToastOverlayTests", () => {
  let sandbox, wrapper

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
    const renderComponent = (extraProps = {}) => {
      const mergedProps = {
        dispatch:         sandbox.stub(),
        messages:         generateMessages(3),
        MessageComponent: DummyMessageComponent,
        ...extraProps
      }
      return mount(<ToastOverlay {...mergedProps} />)
    }

    class DummyMessageComponent extends React.Component<*, void> {
      render() {
        return <div />
      }
    }

    describe("when there are no messages", () => {
      beforeEach(() => {
        wrapper = renderComponent({ messages: [] })
      })

      it("renders nothing", () => {
        assert.isTrue(wrapper.isEmptyRender())
      })
    })

    describe("when there are messages", () => {
      beforeEach(() => {
        wrapper = renderComponent({
          messages:         generateMessages(3),
          MessageComponent: DummyMessageComponent
        })
      })

      it("renders messages with MessageComponent in transition group", () => {
        const messages = wrapper.prop("messages")
        assert.isTrue(messages.length > 0)
        const keyedMessages = _.keyBy(messages, "key")
        const transitionGroupEl = wrapper.find("TransitionGroup")
        const cssTransitionEls = transitionGroupEl.find("CSSTransition")
        assert.equal(cssTransitionEls.length, messages.length)
        cssTransitionEls.forEach(cssTransitionEl => {
          const messageEl = cssTransitionEl.find(
            wrapper.prop("MessageComponent")
          )
          const expectedMessage = keyedMessages[messageEl.key()]
          assert.equal(messageEl.prop("message"), expectedMessage)
        })
      })

      it("passes removeMessage to MessageComponent", () => {
        const messages = wrapper.prop("messages")
        assert.isTrue(messages.length > 0)
        const messageEls = wrapper.find(wrapper.prop("MessageComponent"))
        const removeMessageStub = sandbox.stub(
          wrapper.instance(),
          "removeMessage"
        )
        messageEls.forEach((messageEl, i) => {
          assert.equal(removeMessageStub.callCount, i)
          messageEl.prop("removeMessage")()
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
      return mount(<ToastMessage {...mergedProps} />)
    }

    it("renders the message", () => {
      const message = generateMessage()
      const wrapper = renderComponent({ message })
      assert.equal(wrapper.find(".message-content").text(), message.content)
    })

    describe("icon", () => {
      describe("when icon is present", () => {
        const icon = "someIcon"
        const message = generateMessage(1, { icon })

        it("it renders icon", () => {
          const wrapper = renderComponent({ message })
          assert.equal(wrapper.find(".message-icon").text(), message.icon)
        })
      })

      describe("when icon is absent", () => {
        const message = _.omit(generateMessage(), ["icon"])

        it("it does not render icon", () => {
          const wrapper = renderComponent({ message })
          assert.equal(wrapper.find(".message-icon").length, 0)
        })
      })
    })
  })
})
