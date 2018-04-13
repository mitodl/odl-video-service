// @flow
/* global SETTINGS: false */
import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"
import R from "ramda"
import _ from "lodash"
import DocumentTitle from "react-document-title"

import WithDrawer from "./WithDrawer"
import VideoCard from "../components/VideoCard"
import Button from "../components/material/Button"
import AnalyticsDialog from "../components/dialogs/AnalyticsDialog"
import EditVideoFormDialog from "../components/dialogs/EditVideoFormDialog"
import ShareVideoDialog from "../components/dialogs/ShareVideoDialog"
import DeleteVideoDialog from "../components/dialogs/DeleteVideoDialog"
import CollectionFormDialog from "../components/dialogs/CollectionFormDialog"
import { withDialogs } from "../components/dialogs/hoc"
import DropboxChooser from "react-dropbox-chooser"

import { actions } from "../actions"
import * as collectionUiActions from "../actions/collectionUi"
import { getActiveCollectionDetail } from "../lib/collection"
import { DIALOGS } from "../constants"

import type { Collection } from "../flow/collectionTypes"
import type { Video } from "../flow/videoTypes"
import type { CommonUiState } from "../reducers/commonUi"
import * as commonUiActions from "../actions/commonUi"
import VideoSaverScript from "../components/VideoSaverScript"

export class CollectionDetailPage extends React.Component<*, void> {
  props: {
    dispatch: Dispatch,
    collection: ?Collection,
    collectionError: ?Object,
    collectionKey: string,
    editable: boolean,
    needsUpdate: boolean,
    commonUi: CommonUiState,
    showDialog: Function
  }

  componentDidMount() {
    this.updateRequirements()
  }

  componentDidUpdate() {
    if (!this.props.collectionError) {
      this.updateRequirements()
    }
  }

  updateRequirements = () => {
    const { dispatch, needsUpdate, collectionKey } = this.props
    if (needsUpdate) {
      dispatch(actions.collections.get(collectionKey))
    }
  }

  showEditCollectionDialog = (e: MouseEvent) => {
    const { dispatch, collection } = this.props
    e.preventDefault()
    if (!collection) throw new Error("Collection does not exist")
    dispatch(collectionUiActions.showEditCollectionDialog(collection))
  }

  showVideoMenu = (videoKey: string) => {
    const { dispatch } = this.props
    dispatch(collectionUiActions.setSelectedVideoKey(videoKey))
    dispatch(commonUiActions.showMenu(videoKey))
  }

  closeVideoMenu = (videoKey: string) => {
    const { dispatch } = this.props
    dispatch(collectionUiActions.setSelectedVideoKey(videoKey))
    dispatch(commonUiActions.hideMenu(videoKey))
  }

  showVideoDialog = R.curry((dialogName: string, videoKey: string) => {
    const { dispatch, showDialog } = this.props
    dispatch(collectionUiActions.setSelectedVideoKey(videoKey))
    showDialog(dialogName)
  })

  showEditVideoDialog = this.showVideoDialog(DIALOGS.EDIT_VIDEO)

  showShareVideoDialog = this.showVideoDialog(DIALOGS.SHARE_VIDEO)

  showDeleteVideoDialog = this.showVideoDialog(DIALOGS.DELETE_VIDEO)

  showAnalyticsVideoDialog = this.showVideoDialog(DIALOGS.ANALYTICS)

  handleUpload = async (chosenFiles: Array<Object>) => {
    const { dispatch, collection } = this.props
    if (!collection) throw new Error("Collection does not exist")
    await dispatch(actions.uploadVideo.post(collection.key, chosenFiles))
    // Reload the collection after the video upload request succeeds
    dispatch(actions.collections.get(collection.key))
  }

  renderCollectionDescription = (description: ?string) =>
    !_.isEmpty(description) ? (
      <p className="description">{description}</p>
    ) : null

  renderEmptyVideoMessage = () => (
    <div className="no-videos">
      <h3>You have not added any videos yet.</h3>
      <p>Click the button above to add videos from a linked Dropbox account.</p>
    </div>
  )

  renderCollectionVideos = (videos: Array<Video>, isAdmin: boolean) => (
    <div className="videos">
      {videos.map(
        video => (
          <VideoCard
            video={video}
            key={video.key}
            isAdmin={isAdmin}
            showAnalyticsDialog={this.showAnalyticsVideoDialog.bind(
              this,
              video.key
            )}
            showDeleteDialog={this.showDeleteVideoDialog.bind(this, video.key)}
            showEditDialog={this.showEditVideoDialog.bind(this, video.key)}
            showShareDialog={this.showShareVideoDialog.bind(this, video.key)}
            showVideoMenu={this.showVideoMenu.bind(this, video.key)}
            closeVideoMenu={this.closeVideoMenu.bind(this, video.key)}
            isMenuOpen={this.props.commonUi.menuVisibility[video.key]}
          />
        ),
        this
      )}
    </div>
  )

  renderBody(collection: Collection) {
    const videos = collection.videos || []
    const collectionTitle =
      videos.length === 0
        ? collection.title
        : `${collection.title} (${videos.length})`

    return (
      <div className="centered-content">
        <header>
          <div className="text">
            <h1 className="mdc-typography--title">{collectionTitle}</h1>
          </div>
          <div className="tools">
            {collection.is_admin && [
              <a
                id="edit-collection-button"
                key="settings"
                onClick={this.showEditCollectionDialog}
              >
                <i className="material-icons">settings</i>
              </a>,
              <DropboxChooser
                key="upload"
                appKey={SETTINGS.dropbox_key}
                success={this.handleUpload}
                linkType="direct"
                multiselect={true}
                extensions={["video"]}
              >
                <Button className="dropbox-btn mdc-button--unelevated mdc-ripple-upgraded">
                  <img
                    src="/static/images/dropbox_logo.png"
                    alt="Dropbox Icon"
                  />
                  Add Videos from Dropbox
                </Button>
              </DropboxChooser>
            ]}
          </div>
          {videos.length > 0
            ? this.renderCollectionDescription(collection.description)
            : this.renderEmptyVideoMessage()}
        </header>
        {this.renderCollectionVideos(videos, collection.is_admin)}
      </div>
    )
  }

  render() {
    const { collection } = this.props

    if (!collection) return null

    const detailBody = this.renderBody(collection)

    return (
      <DocumentTitle title={`OVS | ${collection.title}`}>
        <WithDrawer>
          <VideoSaverScript />
          <div className="collection-detail-content">{detailBody}</div>
        </WithDrawer>
      </DocumentTitle>
    )
  }

  getDialogComponent(dialogName: string) {
    switch (dialogName) {
    case DIALOGS.COLLECTION_FORM:
      return CollectionFormDialog
    case DIALOGS.ANALYTICS:
      return AnalyticsDialog
    case DIALOGS.EDIT_VIDEO:
      return EditVideoFormDialog
    case DIALOGS.SHARE_VIDEO:
      return ShareVideoDialog
    case DIALOGS.DELETE_VIDEO:
      return DeleteVideoDialog
    }
    throw Error(`unknown dialog '${dialogName}'`)
  }
}

const mapStateToProps = (state, ownProps) => {
  const { match } = ownProps
  const { collections, commonUi } = state

  const collection =
    collections.loaded && collections.data ? collections.data : null
  const collectionError = collections.error || null
  const collectionKey = match.params.collectionKey
  const activeCollection = getActiveCollectionDetail(state)
  const collectionChanged =
    activeCollection && activeCollection.key !== collectionKey
  const needsUpdate =
    (!collections.processing && !collections.loaded) || collectionChanged

  return {
    collectionKey,
    collection,
    collectionError,
    needsUpdate,
    commonUi
  }
}

const ConnectedCollectionDetailPage = R.compose(
  connect(mapStateToProps),
  withDialogs(
    [
      DIALOGS.COLLECTION_FORM,
      DIALOGS.ANALYTICS,
      DIALOGS.EDIT_VIDEO,
      DIALOGS.SHARE_VIDEO,
      DIALOGS.DELETE_VIDEO
    ].map(dialogName => {
      const dialogConfig = {
        name:         dialogName,
        getComponent: () => {
          return CollectionDetailPage.prototype.getDialogComponent(dialogName)
        }
      }
      return dialogConfig
    })
  )
)(CollectionDetailPage)

export default ConnectedCollectionDetailPage
