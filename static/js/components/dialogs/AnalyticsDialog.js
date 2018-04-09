// @flow
import React from "react"
import _ from "lodash"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import { getVideoWithKey } from "../../lib/collection"

import Button from "../material/Button"
import Dialog from "../material/Dialog"
import LoadingIndicator from "../material/LoadingIndicator"

import AnalyticsPane from "../analytics/AnalyticsPane"
import type { Video } from "../../flow/videoTypes"
import { actions } from "../../actions"

type DialogProps = {
  video: Video,
  dispatch: Dispatch,
  analyticsForVideo: ?Object,
  analyticsNeedsUpdate: boolean,
  error: ?Object,
  open: boolean,
  hideDialog: Function,
  processing: boolean
}

export class AnalyticsDialog extends React.Component<*, void> {
  props: DialogProps

  componentDidMount() {
    this.updateRequirements()
  }

  componentDidUpdate() {
    this.updateRequirements()
  }

  updateRequirements = () => {
    const { error, open, video, analyticsNeedsUpdate } = this.props
    if (open && analyticsNeedsUpdate && !error) {
      this.dispatchVideoAnalyticsGet(video.key)
    }
  }

  dispatchVideoAnalyticsGet(videoKey: string) {
    const { dispatch } = this.props
    dispatch(actions.videoAnalytics.get(videoKey))
  }

  dispatchVideoAnalyticsClear() {
    const { dispatch } = this.props
    dispatch(actions.videoAnalytics.clear())
  }

  render() {
    const { processing, open, hideDialog } = this.props
    const style = {}
    if (!processing) {
      style.minHeight = "90%"
    }
    return (
      <Dialog
        id="analytics-dialog"
        cancelText="Close"
        open={open}
        hideDialog={hideDialog}
        noSubmit={true}
        style={style}
      >
        <div className="mdc-form-field mdc-form-field--align-end">
          {this.renderDialogBody()}
        </div>
      </Dialog>
    )
  }

  renderDialogBody() {
    if (this.props.error) {
      return this.renderErrorUI()
    }
    if (this.props.processing) {
      return this.renderLoadingUI()
    } else if (this.props.analyticsForVideo) {
      return this.renderAnalyticsUI()
    }
    return null
  }

  renderAnalyticsUI() {
    const { video, analyticsForVideo } = this.props
    return <AnalyticsPane video={video} analyticsData={analyticsForVideo} />
  }

  renderLoadingUI() {
    return <LoadingIndicator />
  }

  renderErrorUI() {
    return (
      <section
        className="analytics-dialog-error-ui"
        style={{ textAlign: "center" }}
      >
        <div>Sorry! There was an error while fetching analytics data</div>
        <Button
          className="try-again-button"
          onClick={() => {
            this.dispatchVideoAnalyticsClear()
          }}
        >
          Try again?
        </Button>
      </section>
    )
  }
}

const mapStateToProps = (state, ownProps) => {
  // The dialog needs a video object.
  // This video can be provided (1) directly as a prop,
  // or (2) as (videoKey, collection) combination.
  // The provisioning method will depend on the container that includes this
  // dialog (e.g. VideoDetail vs. CollectionDetail).
  const { collectionUi: { selectedVideoKey } } = state
  let { video } = ownProps
  if (!video && ownProps.collection) {
    video = getVideoWithKey(ownProps.collection, selectedVideoKey)
  }
  // Get analytics if already fetched.
  const { videoAnalytics } = state
  const analyticsForVideo =
    video && videoAnalytics && _.isFunction(videoAnalytics.data.get)
      ? videoAnalytics.data.get(video.key)
      : undefined
  // Indicate whether analytics should be fetched
  const { loaded, error, processing } = videoAnalytics
  let analyticsNeedsUpdate = false
  if (loaded) {
    analyticsNeedsUpdate = analyticsForVideo === undefined
  } else {
    analyticsNeedsUpdate = !processing
  }
  return { video, processing, error, analyticsForVideo, analyticsNeedsUpdate }
}

export const ConnectedAnalyticsDialog = connect(mapStateToProps)(
  AnalyticsDialog
)
export default ConnectedAnalyticsDialog
