// @flow
/* global SETTINGS: false */
import React from 'react';
import { connect } from 'react-redux';
import type { Dispatch } from 'redux';
import _ from 'lodash';

import Dialog from "../material/Dialog";
import Radio from "../material/Radio";
import Textfield from "../material/Textfield";
import Textarea from "../material/Textarea";

import * as videoActions from '../../actions/videoUi';
import { actions } from '../../actions';
import { getVideoWithKey } from '../../lib/collection';
import {
  PERM_CHOICE_NONE,
  PERM_CHOICE_LISTS,
  PERM_CHOICE_PUBLIC,
  PERM_CHOICE_COLLECTION, PERM_CHOICE_OVERRIDE
} from '../../lib/dialog';

import type { Video, VideoUiState } from '../../flow/videoTypes';
import { calculateListPermissionValue } from "../../util/util";
import {setVideoFormErrors} from "../../actions/videoUi";
import {videoHasError, videoIsProcessing} from "../../lib/video";

type DialogProps = {
  dispatch: Dispatch,
  videoUi: VideoUiState,
  video: ?Video,
  open: boolean,
  hideDialog: Function,
  shouldUpdateCollection: boolean
};

class EditVideoFormDialog extends React.Component {
  props: DialogProps;

  componentDidMount() {
    this.checkActiveVideo();
  }

  componentDidUpdate() {
    this.checkActiveVideo();
  }

  checkActiveVideo() {
    const {
      open,
      video,
      videoUi: { editVideoForm }
    } = this.props;
    if (open && video && video.key !== editVideoForm.key) {
      this.initializeFormWithVideo(video);
    }
  }

  determineViewChoice(video: Video) {
    if (video.is_private) {
      return PERM_CHOICE_NONE;
    } else if (video.is_public) {
      return PERM_CHOICE_PUBLIC;
    } else if (video.view_lists.length > 0) {
      return PERM_CHOICE_LISTS;
    } else {
      return PERM_CHOICE_COLLECTION;
    }
  }

  initializeFormWithVideo(video: Video) {
    const { dispatch } = this.props;

    let viewChoice = this.determineViewChoice(video);

    dispatch(videoActions.initEditVideoForm({
      key: video.key,
      title: video.title,
      description: video.description,
      overrideChoice: viewChoice === PERM_CHOICE_COLLECTION ? PERM_CHOICE_COLLECTION : PERM_CHOICE_OVERRIDE,
      viewChoice: viewChoice,
      viewLists:  _.join(video.view_lists, ',')
    }));
  }

  setEditVideoTitle = (event: Object) => {
    const { dispatch } = this.props;
    dispatch(videoActions.setEditVideoTitle(event.target.value));
  };

  setEditVideoDesc = (event: Object) => {
    const { dispatch } = this.props;
    dispatch(videoActions.setEditVideoDesc(event.target.value));
  };

  setVideoViewPermChoice = (choice: string) => {
    const { dispatch, videoUi: { editVideoForm } } = this.props;
    if (choice !== editVideoForm.viewChoice) {
      dispatch(videoActions.setViewChoice(choice));
    }
  };

  handleVideoViewPermClick = (event: Object) => {
    this.setVideoViewPermChoice(event.target.value);
  };

  setVideoPermOverrideChoice = (choice: boolean) => {
    const { dispatch, videoUi: { editVideoForm } } = this.props;
    if (choice !== editVideoForm.overrideChoice) {
      dispatch(videoActions.setPermOverrideChoice(choice));
    }
  }

  handleVideoPermOverrideClick = (event: Object) => {
    this.setVideoPermOverrideChoice(event.target.value);
  };

  setVideoViewPermLists = (event: Object) => {
    const { dispatch } = this.props;
    dispatch(videoActions.setViewLists(event.target.value));
  };

  onClose = ()=> {
    const { hideDialog, dispatch } = this.props;
    dispatch(videoActions.clearVideoForm());
    hideDialog();
  };

  handleError = (error: Error) => {
    const { dispatch, videoUi: { editVideoForm } } = this.props;
    dispatch(
      setVideoFormErrors({
        ...editVideoForm,
        errors: error
      })
    );
  };

  submitForm = async () => {
    const {
      dispatch,
      videoUi: { editVideoForm },
      shouldUpdateCollection
    } = this.props;

    const overridePerms = editVideoForm.overrideChoice === PERM_CHOICE_OVERRIDE;

    let patchData = {
      title: editVideoForm.title,
      description: editVideoForm.description,
    };

    if (SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS) {
      _.assign(patchData, {
        view_lists: overridePerms
          ? calculateListPermissionValue(editVideoForm.viewChoice, editVideoForm.viewLists)
          : [],
        is_public: overridePerms && editVideoForm.viewChoice === PERM_CHOICE_PUBLIC,
        is_private: overridePerms && editVideoForm.viewChoice === PERM_CHOICE_NONE
      });
    }

    try {
      let video = await dispatch(actions.videos.patch(editVideoForm.key, patchData));
      this.initializeFormWithVideo(video);
      if (shouldUpdateCollection) {
        dispatch(actions.collections.get(video.collection_key));
      }
      this.onClose();
    } catch (e) {
      this.handleError(e);
    }
  };

  renderPermissions() {
    const {
      videoUi: { editVideoForm, errors },
      video
    } = this.props;

    const defaultPerms = editVideoForm.overrideChoice === PERM_CHOICE_COLLECTION;

    return <section className="permission-group">
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
        {`${video && video.collection_view_lists.length > 0
          ? _.map(video.collection_view_lists).join(',')
          : 'Only me'}`
        }
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
            onFocus={this.setVideoViewPermChoice.bind(this, PERM_CHOICE_LISTS)}
            value={editVideoForm.viewLists || (video ? _.map(video.view_lists).join(',') : '')}
            validationMessage={errors ? errors.view_lists : ''}
          />
        </Radio>
        <Radio
          id="view-public"
          label="Public - Subtitles are required for this option"
          radioGroupName="video-view-perms"
          value={PERM_CHOICE_PUBLIC}
          selectedValue={editVideoForm.viewChoice}
          onChange={this.handleVideoViewPermClick}
          className="wideLabel"
          // $FlowFixMe
          disabled={defaultPerms || video && video.videosubtitle_set.length === 0}
        />
      </section>
    </section>;
  }

  render() {
    const {
      open,
      hideDialog,
      video,
      videoUi: { editVideoForm, errors },
    } = this.props;

    return <Dialog
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
          validationMessage={errors ? errors.title : ''}
        />
        <Textarea
          label="Description"
          id="video-description"
          onChange={this.setEditVideoDesc}
          value={editVideoForm.description}
        />
        { (SETTINGS.FEATURES.ENABLE_VIDEO_PERMISSIONS && video &&
           !(videoIsProcessing(video)) &&
           !(videoHasError(video)) &&
           this.renderPermissions())
        }
      </div>
    </Dialog>;
  }
}

const mapStateToProps = (state, ownProps) => {
  const { videoUi, collectionUi: { selectedVideoKey } } = state;
  const { collection, video } = ownProps;

  // The dialog needs a Video object passed in as a prop. Depending on the container that includes this dialog,
  // that video can be retrieved in a couple different ways.
  let selectedVideo, shouldUpdateCollection;
  if (video) {
    selectedVideo = video;
    shouldUpdateCollection = false;
  }
  else if (collection) {
    selectedVideo = getVideoWithKey(collection, selectedVideoKey);
    shouldUpdateCollection = true;
  }

  return {
    videoUi: videoUi,
    video: selectedVideo,
    shouldUpdateCollection: shouldUpdateCollection
  };
};

export default connect(mapStateToProps)(EditVideoFormDialog);
