// @flow
/* global SETTINGS: false */
import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"
import _ from "lodash"

import Dialog from "../material/Dialog"
import Filefield from "../material/Filefield"
import Radio from "../material/Radio"
import Textfield from "../material/Textfield"
import Textarea from "../material/Textarea"

import { actions } from "../../actions"
import { getVideoWithKey } from "../../lib/collection"
import { uploadThumbnail } from "../../lib/api"
import {
  PERM_CHOICE_NONE,
  PERM_CHOICE_LISTS,
  PERM_CHOICE_PUBLIC,
  PERM_CHOICE_COLLECTION,
  PERM_CHOICE_OVERRIDE,
  PERM_CHOICE_LOGGED_IN
} from "../../lib/dialog"

import type { Video, VideoUiState } from "../../flow/videoTypes"
import { calculateListPermissionValue } from "../../util/util"
import { videoHasError, videoIsProcessing } from "../../lib/video"

type DialogProps = {
  dispatch: Dispatch,
  videoUi: VideoUiState,
  video: ?Video,
  open: boolean,
  hideDialog: Function,
  shouldUpdateCollection: boolean
}

type DialogState = {
  thumbnailFile: ?File,
  thumbnailPreviewUrl: ?string,
  thumbnailError: ?string
}

/**
 * Allow only blob: (local preview) and https: (CDN) URLs in img src to prevent
 * javascript: or data: URI injection (satisfies CodeQL DOM-XSS check).
 */
function sanitizeImgSrc(url: ?string): string {
  if (!url) return ""
  try {
    const parsed = new URL(url)
    if (parsed.protocol === "blob:" || parsed.protocol === "https:") {
      return parsed.href
    }
  } catch (_) {
    /* invalid URL */
  }
  return ""
}

class EditVideoFormDialog extends React.Component<*, DialogState> {
  props: DialogProps
  state: DialogState = {
    thumbnailFile:       null,
    thumbnailPreviewUrl: null,
    thumbnailError:      null
  }

  componentDidMount() {
    this.checkActiveVideo()
  }

  componentDidUpdate() {
    this.checkActiveVideo()
  }

  checkActiveVideo() {
    const {
      open,
      video,
      videoUi: { editVideoForm }
    } = this.props
    if (open && video && video.key !== editVideoForm.key) {
      this.initializeFormWithVideo(video)
    }
  }

  determineViewChoice(video: Video) {
    if (video.is_private) {
      return PERM_CHOICE_NONE
    } else if (video.is_public) {
      return PERM_CHOICE_PUBLIC
    } else if (video.is_logged_in_only) {
      return PERM_CHOICE_LOGGED_IN
    } else if (video.view_lists.length > 0) {
      return PERM_CHOICE_LISTS
    } else {
      return PERM_CHOICE_COLLECTION
    }
  }

  initializeFormWithVideo(video: Video) {
    const { dispatch } = this.props

    const viewChoice = this.determineViewChoice(video)

    dispatch(
      actions.videoUi.initEditVideoForm({
        key:            video.key,
        title:          video.title,
        description:    video.description,
        cta_link:       video.cta_link || null,
        overrideChoice:
          viewChoice === PERM_CHOICE_COLLECTION ?
            PERM_CHOICE_COLLECTION :
            PERM_CHOICE_OVERRIDE,
        viewChoice: viewChoice,
        viewLists:  _.join(video.view_lists, ",")
      })
    )
  }

  setEditVideoTitle = (event: Object) => {
    const { dispatch } = this.props
    dispatch(actions.videoUi.setEditVideoTitle(event.target.value))
  }

  setEditVideoDesc = (event: Object) => {
    const { dispatch } = this.props
    dispatch(actions.videoUi.setEditVideoDesc(event.target.value))
  }

  setEditVideoCtaLink = (event: Object) => {
    const { dispatch } = this.props
    dispatch(actions.videoUi.setEditVideoCtaLink(event.target.value))
  }

  setVideoViewPermChoice = (choice: string) => {
    const {
      dispatch,
      videoUi: { editVideoForm }
    } = this.props
    if (choice !== editVideoForm.viewChoice) {
      dispatch(actions.videoUi.setViewChoice(choice))
    }
  }

  handleVideoViewPermClick = (event: Object) => {
    this.setVideoViewPermChoice(event.target.value)
  }

  setVideoPermOverrideChoice = (choice: boolean) => {
    const {
      dispatch,
      videoUi: { editVideoForm }
    } = this.props
    if (choice !== editVideoForm.overrideChoice) {
      dispatch(actions.videoUi.setPermOverrideChoice(choice))
    }
  }

  handleVideoPermOverrideClick = (event: Object) => {
    this.setVideoPermOverrideChoice(event.target.value)
  }

  setVideoViewPermLists = (event: Object) => {
    const { dispatch } = this.props
    dispatch(actions.videoUi.setViewLists(event.target.value))
  }

  handleThumbnailChange = (event: Object) => {
    const file = event.target.files[0]
    if (!file) return
    if (file.type !== "image/jpeg" && file.type !== "image/jpg" && file.type !== "image/png") {
      this.setState({
        thumbnailError:      "Only JPEG and PNG image files are allowed.",
        thumbnailFile:       null,
        thumbnailPreviewUrl: null
      })
      event.target.value = ""
      return
    }
    if (file.size > SETTINGS.thumbnail_upload_max_size) {
      this.setState({
        thumbnailError:      `This image is too large (max ${SETTINGS.thumbnail_upload_max_size / (1024 * 1024)} MB). Please reduce the file size and try again.`,
        thumbnailFile:       null,
        thumbnailPreviewUrl: null
      })
      event.target.value = ""
      return
    }
    const { thumbnailPreviewUrl } = this.state
    if (thumbnailPreviewUrl) {
      URL.revokeObjectURL(thumbnailPreviewUrl)
    }
    this.setState({
      thumbnailFile:       file,
      thumbnailPreviewUrl: URL.createObjectURL(file),
      thumbnailError:      null
    })
  }

  onClose = () => {
    const { hideDialog, dispatch } = this.props
    const { thumbnailPreviewUrl } = this.state
    if (thumbnailPreviewUrl) {
      URL.revokeObjectURL(thumbnailPreviewUrl)
    }
    this.setState({
      thumbnailFile:       null,
      thumbnailPreviewUrl: null,
      thumbnailError:      null
    })
    dispatch(actions.videoUi.clearVideoForm())
    hideDialog()
  }

  handleError = (error: Error) => {
    const {
      dispatch,
      videoUi: { editVideoForm }
    } = this.props
    dispatch(
      actions.videoUi.setVideoFormErrors({
        ...editVideoForm,
        errors: error
      })
    )
  }

  submitForm = async () => {
    const {
      dispatch,
      videoUi: { editVideoForm },
      shouldUpdateCollection
    } = this.props

    const overridePerms = editVideoForm.overrideChoice === PERM_CHOICE_OVERRIDE

    let patchData = {
      title:       editVideoForm.title,
      description: editVideoForm.description,
      ...(editVideoForm.cta_link !== null ?
        { cta_link: editVideoForm.cta_link || null } :
        {})
    }

    if (SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS) {
      patchData = {
        ...patchData,
        view_lists: overridePerms ?
          calculateListPermissionValue(
            editVideoForm.viewChoice,
            editVideoForm.viewLists
          ) :
          [],
        is_public:
          overridePerms && editVideoForm.viewChoice === PERM_CHOICE_PUBLIC,
        is_private:
          overridePerms && editVideoForm.viewChoice === PERM_CHOICE_NONE,
        is_logged_in_only:
          overridePerms && editVideoForm.viewChoice === PERM_CHOICE_LOGGED_IN
      }
    }

    try {
      const { thumbnailFile } = this.state
      if (thumbnailFile) {
        const formData = new FormData()
        formData.append("thumbnail", thumbnailFile)
        try {
          await uploadThumbnail(editVideoForm.key, formData)
        } catch (uploadErr) {
          this.setState({
            thumbnailError:      uploadErr.message,
            thumbnailFile:       null,
            thumbnailPreviewUrl: null
          })
          return
        }
      }
      const video = await dispatch(
        actions.videos.patch(editVideoForm.key, patchData)
      )
      this.initializeFormWithVideo(video)
      if (shouldUpdateCollection) {
        dispatch(actions.collections.get(video.collection_key))
      }
      this.addToastMessage({
        message: {
          key:     "video-saved",
          content: "Changes saved",
          icon:    "check"
        }
      })
      this.onClose()
    } catch (e) {
      this.handleError(e)
    }
  }

  addToastMessage(...args) {
    const { dispatch } = this.props
    dispatch(actions.toast.addMessage(...args))
  }

  renderThumbnail() {
    const { video } = this.props
    const { thumbnailPreviewUrl, thumbnailError } = this.state
    const existingThumbnail =
      video && video.videothumbnail_set && video.videothumbnail_set.length > 0 ?
        video.videothumbnail_set[0] :
        null

    const previewUrl =
      thumbnailPreviewUrl ||
      (existingThumbnail ? existingThumbnail.cloudfront_url : null)

    const buttonLabel = existingThumbnail ?
      "Replace thumbnail" :
      "Add thumbnail"

    return (
      <section className="thumbnail-group">
        <h4 className="mdc-typography--subheading2">Thumbnail</h4>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {previewUrl && (
            <img
              src={sanitizeImgSrc(previewUrl)}
              alt="Video thumbnail"
              style={{
                width:        "120px",
                height:       "68px",
                objectFit:    "cover",
                borderRadius: "4px",
                border:       "1px solid #ccc",
                flexShrink:   0
              }}
            />
          )}
          <Filefield
            label={buttonLabel}
            accept="image/jpeg,image/jpg,image/png,.jpg,.jpeg,.png"
            onChange={this.handleThumbnailChange}
          />
          {thumbnailError ? (
            <p
              style={{ color: "red", margin: "4px 0 0 0", fontSize: "0.85em" }}
            >
              {thumbnailError}
            </p>
          ) : (
            <p
              style={{ color: "#666", margin: "4px 0 0 0", fontSize: "0.8em" }}
            >
              JPEG or PNG, max {SETTINGS.thumbnail_upload_max_size / (1024 * 1024)} MB
            </p>
          )}
        </div>
      </section>
    )
  }

  renderPermissions() {
    const {
      videoUi: { editVideoForm, errors },
      video,
      collection
    } = this.props

    const defaultPerms = editVideoForm.overrideChoice === PERM_CHOICE_COLLECTION
    const collectionIsPublic = collection ? collection.is_public : false

    return (
      <section className="permission-group">
        <h4>Who can view this video?</h4>
        <Radio
          id="view-collection-inherit"
          label="Same as collection permissions (default)"
          radioGroupName="video-view-perms-override"
          value={PERM_CHOICE_COLLECTION}
          selectedValue={editVideoForm.overrideChoice}
          onChange={this.handleVideoPermOverrideClick}
          className="wideLabel"
        />
        <div className="collectionPerms">
          {`${
            video && video.collection_view_lists.length > 0 ?
              _.map(video.collection_view_lists).join(",") :
              "Only owner"
          }`}
        </div>
        <Radio
          id="view-collection-override"
          label="Override collection permissions for this video"
          radioGroupName="video-view-perms-override"
          value={PERM_CHOICE_OVERRIDE}
          selectedValue={editVideoForm.overrideChoice}
          onChange={this.handleVideoPermOverrideClick}
          className="wideLabel"
        />
        <section className="permission-group nested-once">
          <Radio
            id="view-only-me"
            label="Only you and other admins"
            radioGroupName="video-view-perms"
            value={PERM_CHOICE_NONE}
            selectedValue={editVideoForm.viewChoice}
            onChange={this.handleVideoViewPermClick}
            disabled={defaultPerms}
            className="wideLabel"
          />
          <Radio
            id="view-moira"
            label="Moira Lists"
            radioGroupName="video-view-permss"
            value={PERM_CHOICE_LISTS}
            selectedValue={editVideoForm.viewChoice}
            onChange={this.handleVideoViewPermClick}
            disabled={defaultPerms}
          >
            <Textfield
              id="view-moira-input"
              placeholder="Add Moira list(s), separated by commas"
              onChange={this.setVideoViewPermLists}
              onFocus={this.setVideoViewPermChoice.bind(
                this,
                PERM_CHOICE_LISTS
              )}
              value={
                editVideoForm.viewLists ||
                (video ? _.map(video.view_lists).join(",") : "")
              }
              validationMessage={errors ? errors.view_lists : ""}
            />
          </Radio>
          <Radio
            id="view-logged-in-only"
            label="MIT Touchstone"
            radioGroupName="video-view-perms"
            value={PERM_CHOICE_LOGGED_IN}
            selectedValue={editVideoForm.viewChoice}
            onChange={this.handleVideoViewPermClick}
            disabled={defaultPerms}
            className="wideLabel"
          />
          {collectionIsPublic && (
            <Radio
              id="view-public"
              label="Publicly accessible"
              radioGroupName="video-view-perms"
              value={PERM_CHOICE_PUBLIC}
              selectedValue={editVideoForm.viewChoice}
              onChange={this.handleVideoViewPermClick}
              className="wideLabel"
            />
          )}
        </section>
      </section>
    )
  }

  render() {
    const {
      open,
      hideDialog,
      video,
      videoUi: { editVideoForm, errors }
    } = this.props

    return (
      <Dialog
        id="edit-video-form-dialog"
        title="Edit Video Details"
        cancelText="Cancel"
        submitText="Save Changes"
        noSubmit={false}
        hideDialog={hideDialog}
        onAccept={this.submitForm}
        onCancel={this.onClose}
        open={open}
        validateOnClick={true}
      >
        <div className="ovs-form-dialog">
          <Textfield
            label="Title"
            id="video-title"
            onChange={this.setEditVideoTitle}
            value={editVideoForm.title}
            validationMessage={errors ? errors.title : ""}
            required
          />
          <Textarea
            label="Description"
            id="video-description"
            onChange={this.setEditVideoDesc}
            value={editVideoForm.description}
          />
          <Textfield
            label="Call-to-Action Link"
            id="video-cta-link"
            onChange={this.setEditVideoCtaLink}
            value={editVideoForm.cta_link || ""}
            validationMessage={errors ? errors.cta_link : ""}
            placeholder="https://"
          />
          {video &&
            !videoIsProcessing(video) &&
            !videoHasError(video) &&
            this.renderThumbnail()}
          {SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS &&
            video &&
            !videoIsProcessing(video) &&
            !videoHasError(video) &&
            this.renderPermissions()}
        </div>
      </Dialog>
    )
  }
}

const mapStateToProps = (state, ownProps) => {
  const {
    videoUi,
    collectionUi: { selectedVideoKey }
  } = state
  const { collection, video } = ownProps

  // The dialog needs a Video object passed in as a prop. Depending on the container that includes this dialog,
  // that video can be retrieved in a couple different ways.
  let selectedVideo, shouldUpdateCollection
  if (video) {
    selectedVideo = video
    shouldUpdateCollection = false
  } else if (collection) {
    selectedVideo = getVideoWithKey(collection, selectedVideoKey)
    shouldUpdateCollection = true
  }

  return {
    videoUi:                videoUi,
    video:                  selectedVideo,
    shouldUpdateCollection: shouldUpdateCollection,
    collection:             collection
  }
}

export default connect(mapStateToProps)(EditVideoFormDialog)
