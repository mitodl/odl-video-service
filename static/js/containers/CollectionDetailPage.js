// @flow
/* global SETTINGS: false */
import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"
import R from "ramda"
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
            {collectionError
              ? this.renderError(collectionError)
              : this.renderBody()}
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
    const { collection } = this.props
    if (!collection) {
      return null
    }
    const videos = collection.videos || []
    const isAdmin = collection.is_admin
    return (
      <div className="centered-content">
        <header>
          <div className="text">
            <h1 className="mdc-typography--title">
              {`${collection.title} (${videos.length})`}
            </h1>
          </div>
          {this.renderTools(isAdmin)}
          {this.renderDescription(collection.description)}
        </header>
        {this.renderVideos(videos, isAdmin)}
      </div>
    )
  }

  renderTools(isAdmin: boolean) {
    return <div className="tools">{isAdmin && this.renderAdminTools()}</div>
  }

  renderAdminTools() {
    return [this.renderSettingsFrob(), this.renderUploadFrob()]
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

  async handleUpload(chosenFiles: Array<Object>) {
    const { dispatch, collection } = this.props
    if (!collection) {
      return null
    }
    await dispatch(actions.uploadVideo.post(collection.key, chosenFiles))
    dispatch(actions.collections.get(collection.key))
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
    let message = "There are no public videos available for viewing."
    if (isAdmin) {
      message = "There are no videos yet. Click the button above to add videos from a linked Dropbox account."
    }
    return (
      <div className="no-videos">
        <p>{ message }</p>
      </div>
    )
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

  getDialogComponent(dialogName: string) {
    switch (dialogName) {
    case DIALOGS.COLLECTION_FORM:
      return CollectionFormDialog
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

export const mapStateToProps = (state: any, ownProps: any) => {
  const { match } = ownProps
  const { collections, commonUi } = state

  const collectionKey = match.params.collectionKey
  const collection =
    collections.loaded && collections.data ? collections.data : null
  const collectionError = collections.error || null
  const collectionChanged = collection && collection.key !== collectionKey
  const needsUpdate =
    collectionChanged || (!collections.processing && !collections.loaded)

  return {
    collectionKey,
    collection,
    collectionError,
    needsUpdate,
    commonUi
  }
}

export const ConnectedCollectionDetailPage = R.compose(
  connect(mapStateToProps),
  withDialogs(
    [
      DIALOGS.COLLECTION_FORM,
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
