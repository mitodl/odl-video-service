import React from "react"
import _ from "lodash"
import * as R from "ramda"
import { connect } from "react-redux"
import type { UnknownAction } from "redux"
import type { ThunkAction, ThunkDispatch } from "redux-thunk"

import { actions } from "../actions"
import type { RootState } from "../types/rootState"
import type { Video } from "../types/videoTypes"

/*
 * `actions` is declared `Record<string, unknown>` in actions/index.ts, so each
 * slice comes back as `unknown`. The cast is erased at runtime -- the dispatch
 * below stays a property access on `actions.videoAnalytics`, which is what
 * withVideoAnalytics_test.js stubs -- and only tells tsc the shape
 * redux-hammock's deriveActions produces for the videoAnalytics endpoint.
 */
type VideoAnalyticsActions = {
  get: (
    videoKey: string
  ) => ThunkAction<Promise<unknown>, RootState, unknown, UnknownAction>
}

type Props = {
  dispatch: ThunkDispatch<RootState, unknown, UnknownAction>
  needsUpdate?: boolean
  video?: Video
  // Every other prop is forwarded untouched to the wrapped component.
  [key: string]: unknown
}

export const withVideoAnalytics = (
  WrappedComponent: React.ComponentType<Record<string, unknown>>
) => {
  return class WithVideoAnalytics extends React.Component<Props> {
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
      const videoAnalyticsActions =
        actions.videoAnalytics as VideoAnalyticsActions
      this.props.dispatch(videoAnalyticsActions.get(this.props.video.key))
    }
  }
}

export const mapStateToProps = (
  state: Partial<RootState> = {},
  ownProps: { video?: Video } = {}
) => {
  const { videoAnalytics } = state
  const { video } = ownProps
  const needsUpdate =
    video && !videoAnalytics.processing && !videoAnalytics.loaded
  return { video, videoAnalytics, needsUpdate }
}

export default R.compose(connect(mapStateToProps), withVideoAnalytics)
