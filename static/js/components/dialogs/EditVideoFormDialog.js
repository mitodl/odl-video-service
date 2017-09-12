// @flow
import React from 'react';
import { connect } from 'react-redux';
import type { Dispatch } from 'redux';

import Dialog from "../material/Dialog";
import Textfield from "../material/Textfield";
import Textarea from "../material/Textarea";

import * as uiActions from '../../actions/commonUi';
import { actions } from '../../actions';
import { getVideoWithKey } from '../../lib/collection';

import type { CommonUiState } from "../../reducers/commonUi";
import type { Video } from '../../flow/videoTypes';

type DialogProps = {
  dispatch: Dispatch,
  commonUi: CommonUiState,
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
      commonUi: { editVideoForm }
    } = this.props;
    if (open && video && video.key !== editVideoForm.key) {
      this.initializeFormWithVideo(video);
    }
  }

  initializeFormWithVideo(video: Video) {
    const { dispatch } = this.props;
    dispatch(uiActions.initEditVideoForm({
      key: video.key,
      title: video.title,
      description: video.description
    }));
  }

  setEditVideoTitle = (event: Object) => {
    const { dispatch } = this.props;
    dispatch(uiActions.setEditVideoTitle(event.target.value));
  };

  setEditVideoDesc = (event: Object) => {
    const { dispatch } = this.props;
    dispatch(uiActions.setEditVideoDesc(event.target.value));
  };

  submitForm = async () => {
    const {
      dispatch,
      hideDialog,
      commonUi: { editVideoForm },
      shouldUpdateCollection
    } = this.props;

    let patchData = {
      title: editVideoForm.title,
      description: editVideoForm.description
    };
    let video = await dispatch(actions.videos.patch(editVideoForm.key, patchData));
    hideDialog();
    this.initializeFormWithVideo(video);
    if (shouldUpdateCollection) {
      dispatch(actions.collections.get(video.collection_key));
    }
  };

  render() {
    const {
      open,
      hideDialog,
      commonUi: { editVideoForm }
    } = this.props;

    return <Dialog
      id="edit-video-form-dialog"
      title="Edit Video Details"
      cancelText="Cancel"
      submitText="Save Changes"
      noSubmit={false}
      onCancel={hideDialog}
      onAccept={this.submitForm}
      open={open}
    >
      <div className="mdc-form-field mdc-form-field--align-end">
        <Textfield
          label="Title"
          id="video-title"
          onChange={this.setEditVideoTitle}
          value={editVideoForm.title}
        />
        <Textarea
          label="Description"
          id="video-description"
          onChange={this.setEditVideoDesc}
          value={editVideoForm.description}
        />
      </div>
    </Dialog>;
  }
}

const mapStateToProps = (state, ownProps) => {
  const { commonUi, collectionUi: { selectedVideoKey } } = state;
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
    commonUi: commonUi,
    video: selectedVideo,
    shouldUpdateCollection: shouldUpdateCollection
  };
};

export default connect(mapStateToProps)(EditVideoFormDialog);
