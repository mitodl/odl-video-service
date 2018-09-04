// @flow
import React from "react"
import _ from "lodash"
import { connect } from "react-redux"
import type { Dispatch } from "redux"
import { CSSTransition, TransitionGroup } from "react-transition-group"

import { actions } from "../actions"
import type { ToastMessage as ToastMessageType } from "../flow/toastTypes"

const DELAY_MS = 3000

export class ToastOverlay extends React.Component<*, void> {
  props: {
    dispatch: Dispatch,
    messages?: Array<ToastMessageType>,
    MessageComponent?: any
  }

  render() {
    const { messages } = this.props
    if (_.isEmpty(messages)) {
      return null
    }
    const MessageComponent = this.props.MessageComponent || ToastMessage
    return (
      <div className="toast-overlay">
        <TransitionGroup className="toast-messages" appear={true}>
          {messages
            ? messages.map(message => {
              return (
                <CSSTransition
                  key={message.key}
                  timeout={1000}
                  classNames="toast-transition"
                  unmountOnExit={true}
                >
                  <MessageComponent
                    key={message.key}
                    removeMessage={(...args) => {
                      this.removeMessage(...args)
                    }}
                    message={message}
                  />
                </CSSTransition>
              )
            })
            : null}
        </TransitionGroup>
      </div>
    )
  }

  removeMessage(opts: { key: string }) {
    this.props.dispatch(actions.toast.removeMessage(opts))
  }
}

export class ToastMessage extends React.Component<*, void> {
  componentDidMount() {
    setTimeout(() => {
      this.props.removeMessage({ key: this.props.message.key })
    }, DELAY_MS)
  }

  render() {
    const { message } = this.props
    return (
      <span className="toast-message">
        {message.icon ? (
          <span className="message-icon">
            <i className="material-icons">{message.icon}</i>
          </span>
        ) : null}
        <span className="message-content">{message.content}</span>
      </span>
    )
  }
}

export const mapStateToProps = (state: Object) => {
  return { messages: state.toast.messages }
}

export const ConnectedToastOverlay = connect(mapStateToProps)(ToastOverlay)

export default ConnectedToastOverlay
