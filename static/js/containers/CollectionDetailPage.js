// @flow
/* global SETTINGS: false */
import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"
import * as R from "ramda"
import _ from "lodash"
import DocumentTitle from "react-document-title"

import WithDrawer from "./WithDrawer"
import VideoList from "../components/VideoList"
import Button from "../components/material/Button"
import EditVideoFormDialog from "../components/dialogs/EditVideoFormDialog"
import ShareVideoDialog from "../components/dialogs/ShareVideoDialog"
import DeleteVideoDialog from "../components/dialogs/DeleteVideoDialog"
import CollectionFormDialog from "../components/dialogs/CollectionFormDialog"
import { withDialogs } from "../components/dialogs/hoc"
import DropboxChooser from "react-dropbox-chooser"
import ErrorMessage from "../components/ErrorMessage"
import * as ErrorMessages from "../components/errorMessages"

import { actions } from "../actions"
import * as collectionUiActions from "../actions/collectionUi"
import { DIALOGS } from "../constants"

import type { Collection } from "../flow/collectionTypes"
import type { Video } from "../flow/videoTypes"
import type { CommonUiState } from "../reducers/commonUi"
import * as commonUiActions from "../actions/commonUi"
import VideoSaverScript from "../components/VideoSaverScript"
import { clearCollectionErrors } from "../actions/collectionUi"

export class CollectionDetailPage extends React.Component<*, void> {
  props: {
    dispatch: Dispatch,
    collection: ?Collection,
    collectionError: ?Object,
    collectionKey: string,
    isCollectionAdmin: boolean,
    editable: boolean,
    needsUpdate: boolean,
    commonUi: CommonUiState,
    showDialog: Function
  }

  componentDidMount() {
    this.updateRequirements()
  }

  updateRequirements() {
    const { dispatch, needsUpdate, collectionKey, collectionError } = this.props
    if (collectionError) {
      dispatch(clearCollectionErrors())
    }
    if (needsUpdate) {
      dispatch(actions.collections.get(collectionKey))
    }
  }

  componentDidUpdate() {
    if (!this.props.collectionError) {
      this.updateRequirements()
    }
  }

  render() {
    const { collection, collectionError } = this.props
    if (!collection && !collectionError) {
      return null
    }
    return (
      <DocumentTitle title={collection ? `OVS | ${collection.title}` : "OVS"}>
        <WithDrawer>
          <VideoSaverScript />
          <div className="collection-detail-content">
            {collectionError ?
              this.renderError(collectionError) :
              this.renderBody()}
          </div>
        </WithDrawer>
      </DocumentTitle>
    )
  }

  renderError(error: any) {
    if (error.detail) {
      return <ErrorMessage>Error: {error.detail}</ErrorMessage>
    }
    return <ErrorMessages.UnableToLoadData />
  }

  renderBody() {
    const { collection, isCollectionAdmin } = this.props
    if (!collection) {
      return null
    }
    const videos = collection.videos || []
    return (
      <div className="centered-content">
        <header>
          <div className="text">
            <h1 className="mdc-typography--title">
              {`${collection.title} (${videos.length})`}
            </h1>
            <div className="collection-owner">
              <span className="mdc-typography--subheading1">Owner: {collection.owner_info.username}</span>
            </div>
          </div>
          {this.renderTools(isCollectionAdmin)}
          {this.renderDescription(collection.description)}
        </header>
        {this.renderVideos(videos, isCollectionAdmin)}
      </div>
    )
  }

  renderTools(isAdmin: boolean) {
    return <div className="tools">{isAdmin && this.renderAdminTools()}</div>
  }

  renderAdminTools() {
    return [this.renderSettingsFrob(), this.renderSyncWithEdXFrob(), this.renderUploadFrob()]
  }

  renderSettingsFrob() {
    return (
      <a
        id="edit-collection-button"
        key="settings"
        onClick={this.showEditCollectionDialog.bind(this)}
      >
        <i className="material-icons">settings</i>
      </a>
    )
  }

  showEditCollectionDialog(e: MouseEvent) {
    const { dispatch, collection } = this.props
    e.preventDefault()
    // $FlowFixMe: collection will really be a colleciton
    dispatch(collectionUiActions.showEditCollectionDialog(collection))
  }

  renderUploadFrob() {
    return (
      <DropboxChooser
        key="upload"
        appKey={SETTINGS.dropbox_key}
        success={this.handleUpload.bind(this)}
        linkType="direct"
        multiselect={true}
        extensions={["video"]}
      >
        <Button className="dropbox-btn mdc-button--unelevated mdc-ripple-upgraded">
          <img src="/static/images/dropbox_logo.png" alt="Dropbox Icon" />
          Add Videos from Dropbox
        </Button>
      </DropboxChooser>
    )
  }

  renderSyncWithEdXFrob() {
    const { collection } = this.props
    // Only show the button if collection exists and has an edX course ID
    if (!collection || !collection.edx_course_id) {
      return null
    }

    return (
      <Button
        key="sync-edx"
        className="sync-edx-btn mdc-button--unelevated mdc-ripple-upgraded"
        onClick={this.handleSyncWithEdX.bind(this)}
      >
        <i className="material-icons" style={{marginRight: "8px"}}>sync</i>
        Sync Videos with edX
      </Button>
    )
  }

  async handleUpload(chosenFiles: Array<Object>) {
    const { dispatch, collection } = this.props
    if (!collection) {
      return null
    }
    await dispatch(actions.uploadVideo.post(collection.key, chosenFiles))
    dispatch(actions.collections.get(collection.key))
  }

  async handleSyncWithEdX(e: Event) {
    e.preventDefault()
    const { dispatch, collectionKey } = this.props
    if (!collectionKey) {
      return null
    }

    try {
      // Import syncCollectionVideosWithEdX from the API
      const { syncCollectionVideosWithEdX } = require("../lib/api")

      // Call the API endpoint
      await syncCollectionVideosWithEdX(collectionKey)

      // Show success message to the user
      dispatch(actions.toast.addMessage({
        message: {
          key:     "scheduled-sync",
          content: "Videos are being synced with edX. This may take a few minutes.",
          icon:    "check"
        }
      }))
    } catch (error) {
      // Extract error message if available
      let errorMessage = "Failed to sync videos with edX"
      console.log("Sync error:", error)
      if (error && error.error) {
        errorMessage = error.error
      }

      // Show error message to the user
      dispatch(actions.toast.addMessage({
        message: {
          key:     "sync-error",
          content: errorMessage,
          icon:    "error"
        }
      }))
    }
  }

  renderDescription(description: ?string) {
    if (_.isEmpty(description)) {
      return null
    }
    return <p className="description">{description}</p>
  }

  renderVideos(videos: Array<Video>, isAdmin: boolean) {
    if (videos.length === 0) {
      return this.renderEmptyVideoMessage(isAdmin)
    }
    return (
      <VideoList
        className="videos"
        videos={videos}
        commonUi={this.props.commonUi}
        isAdmin={isAdmin}
        showDeleteVideoDialog={this.showDeleteVideoDialog.bind(this)}
        showEditVideoDialog={this.showEditVideoDialog.bind(this)}
        showShareVideoDialog={this.showShareVideoDialog.bind(this)}
        showVideoMenu={this.showVideoMenu.bind(this)}
        hideVideoMenu={this.hideVideoMenu.bind(this)}
        isVideoMenuOpen={this.isVideoMenuOpen.bind(this)}
      />
    )
  }

  renderEmptyVideoMessage(isAdmin: boolean) {
    const { collectionKey } = this.props

    let message = (
      <p>
        There are no public videos available for viewing. Please{" "}
        <a href={`/login/?next=/collections/${collectionKey}`}>login</a> to view
        private videos.
      </p>
    )
    if (isAdmin) {
      message = (
        <p>
          There are no videos yet. Click the button above to add videos from a
          linked Dropbox account.
        </p>
      )
    }
    return <div className="no-videos">{message}</div>
  }

  showVideoMenu(videoKey: string) {
    const { dispatch } = this.props
    dispatch(collectionUiActions.setSelectedVideoKey(videoKey))
    dispatch(commonUiActions.showMenu(videoKey))
  }

  hideVideoMenu(videoKey: string) {
    const { dispatch } = this.props
    dispatch(collectionUiActions.setSelectedVideoKey(videoKey))
    dispatch(commonUiActions.hideMenu(videoKey))
  }

  isVideoMenuOpen(videoKey: string) {
    return this.props.commonUi.menuVisibility[videoKey]
  }

  showVideoDialog(dialogName: string, videoKey: string) {
    const { dispatch, showDialog } = this.props
    dispatch(collectionUiActions.setSelectedVideoKey(videoKey))
    showDialog(dialogName)
  }

  showEditVideoDialog(videoKey: string) {
    this.showVideoDialog(DIALOGS.EDIT_VIDEO, videoKey)
  }

  showShareVideoDialog(videoKey: string) {
    this.showVideoDialog(DIALOGS.SHARE_VIDEO, videoKey)
  }

  showDeleteVideoDialog(videoKey: string) {
    this.showVideoDialog(DIALOGS.DELETE_VIDEO, videoKey)
  }
}

const enabledDialogs = {
  [DIALOGS.COLLECTION_FORM]: CollectionFormDialog,
  [DIALOGS.EDIT_VIDEO]:      EditVideoFormDialog,
  [DIALOGS.SHARE_VIDEO]:     ShareVideoDialog,
  [DIALOGS.DELETE_VIDEO]:    DeleteVideoDialog
}

export const mapStateToProps = (state: any, ownProps: any) => {
  const { match } = ownProps
  const { collections, commonUi } = state

  const collectionKey = match.params.collectionKey
  const collection =
    collections.loaded && collections.data ? collections.data : null
  const collectionError = collections.error || null
  const collectionChanged = collection && collection.key !== collectionKey
  const isCollectionAdmin = collection && collection.is_admin
  const needsUpdate =
    collectionChanged || (!collections.processing && !collections.loaded)
  const dialogProps = {
    [DIALOGS.COLLECTION_FORM]: {
      isEdxCourseAdmin: SETTINGS.is_app_admin || SETTINGS.is_edx_course_admin
    }
  }

  return {
    collectionKey,
    collection,
    collectionError,
    isCollectionAdmin,
    needsUpdate,
    commonUi,
    dialogProps
  }
}

export const ConnectedCollectionDetailPage = R.compose(
  connect(mapStateToProps),
  withDialogs(
    Object.keys(enabledDialogs).map(dialogName => {
      return {
        name:      dialogName,
        component: enabledDialogs[dialogName]
      }
    })
  )
)(CollectionDetailPage)

export default ConnectedCollectionDetailPage
