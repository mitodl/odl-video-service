import React from "react"
import _ from "lodash"
import R from "ramda"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import { actions } from "../actions"

export const withVideoAnalytics = WrappedComponent => {
  return class WithVideoAnalytics extends React.Component<*, void> {
    props: {
      dispatch: Dispatch
    }

    render() {
      return <WrappedComponent {...this.generatePropsForWrappedComponent()} />
    }

    generatePropsForWrappedComponent() {
      return _.omit(this.props, ["needsUpdate", "dispatch"])
    }

    componentDidMount() {
      this.updateIfNeeded()
    }

    componentDidUpdate() {
      this.updateIfNeeded()
    }

    updateIfNeeded() {
      if (this.props.needsUpdate) {
        this.update()
      }
    }

    update() {
      this.props.dispatch(actions.videoAnalytics.get(this.props.video.key))
    }
  }
}

export const mapStateToProps = (state = {}, ownProps = {}) => {
  const { videoAnalytics } = state
  const { video } = ownProps
  const needsUpdate =
    video && !videoAnalytics.processing && !videoAnalytics.loaded
  return { video, videoAnalytics, needsUpdate }
}

export default R.compose(
  connect(mapStateToProps),
  withVideoAnalytics
)
