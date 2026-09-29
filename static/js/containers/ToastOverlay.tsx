import React from "react"
import _ from "lodash"
import { connect } from "react-redux"
import type { Dispatch } from "redux"
import { CSSTransition, TransitionGroup } from "react-transition-group"

import { actions } from "../actions"
import type { ToastMessage as ToastMessageType } from "../types/toastTypes"
import type { RootState } from "../types/rootState"
import type { ActionCreator } from "../types/reduxTypes"

export const DELAY_MS = 3000

type ToastMessageProps = {
  message: ToastMessageType
  removeMessage: (opts: { key: string }) => void
}

type ToastOverlayProps = {
  dispatch: Dispatch
  messages?: Array<ToastMessageType>
  MessageComponent?: React.ComponentType<ToastMessageProps>
}

export class ToastOverlay extends React.Component<ToastOverlayProps> {
  render() {
    const { messages } = this.props
    if (_.isEmpty(messages)) {
      return null
    }
    const MessageComponent = this.props.MessageComponent || ToastMessage
    return (
      <div className="toast-overlay">
        <TransitionGroup className="toast-messages" appear={true}>
          {messages ?
            messages.map(message => {
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
            }) :
            null}
        </TransitionGroup>
      </div>
    )
  }

  removeMessage(opts: { key: string }) {
    // `actions` is declared `Record<string, unknown>` in actions/index.ts, so
    // each slice comes back as `unknown`. The cast is erased at runtime -- the
    // call stays a property access on `actions.toast`, which is what the tests
    // stub -- and only tells tsc the shape actions/toast.ts already exports.
    this.props.dispatch(
      (actions.toast as { removeMessage: ActionCreator }).removeMessage(opts)
    )
  }
}

export class ToastMessage extends React.Component<ToastMessageProps> {
  _dismissTimer: ReturnType<typeof setTimeout>

  componentDidMount() {
    this._dismissTimer = setTimeout(() => {
      this.props.removeMessage({ key: this.props.message.key })
    }, DELAY_MS)
  }

  componentWillUnmount() {
    clearTimeout(this._dismissTimer)
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

export const mapStateToProps = (state: RootState) => {
  return { messages: state.toast.messages }
}

export const ConnectedToastOverlay = connect(mapStateToProps)(ToastOverlay)

export default ConnectedToastOverlay
