// @flow
import React from 'react';
import { connect } from 'react-redux';
import moment from 'moment';
import type { Dispatch } from "redux";

import Button from '../components/material/Button';
import Dialog from '../components/material/Dialog';
import Drawer from '../components/material/Drawer';
import Toolbar from '../components/material/Toolbar';
import Footer from '../components/Footer';
import VideoPlayer from '../components/VideoPlayer';
import Textfield from "../components/material/Textfield";

import { actions } from '../actions';
import {
  setDialogVisibility,
  setDrawerOpen,
  setTitle,
  setDescription,
  clearDialog,
} from '../actions/videoDetailUi';
import { makeCollectionUrl } from '../lib/urls';
import { videoIsProcessing, videoHasError } from '../lib/video';
import { MM_DD_YYYY } from '../constants';

import type { Video } from "../flow/videoTypes";
import type { VideoDetailUIState } from "../reducers/videoDetailUi";

class VideoDetailPage extends React.Component {
  props: {
    dispatch: Dispatch,
    video: ?Video,
    videoKey: string,
    needsUpdate: boolean,
    videoDetailUi: VideoDetailUIState,
    editable: boolean
  };

  componentDidMount() {
    this.updateRequirements();
  }

  componentDidUpdate() {
    this.updateRequirements();
  }

  updateRequirements = () => {
    const { dispatch, videoKey, needsUpdate } = this.props;

    if (needsUpdate) {
      dispatch(actions.videos.get(videoKey));
    }
  };

  openDialog = () => {
    const { dispatch, video, editable } = this.props;
    if (video && editable) {
      dispatch(setTitle(video.title));
      dispatch(setDescription(video.description));
    }
    dispatch(setDialogVisibility(true));
  };

  submitForm = () => {
    const { dispatch, videoKey, videoDetailUi } = this.props;
    const { title, description } = videoDetailUi.dialog;

    dispatch(clearDialog());
    dispatch(actions.videos.patch(videoKey, {
      title,
      description,
    }));
  };

  clearDialog = () => {
    const { dispatch } = this.props;
    dispatch(clearDialog());
  };

  setTitle = (event: Object) => {
    const { dispatch } = this.props;
    dispatch(setTitle(event.target.value));
  };

  setDescription = (event: Object) => {
    const { dispatch } = this.props;
    dispatch(setDescription(event.target.value));
  }

  setDrawerOpen = (open: boolean): void => {
    const { dispatch } = this.props;
    dispatch(setDrawerOpen(open));
  };

  renderVideoPlayer = (video: Video) => {
    if (videoIsProcessing(video)) {
      return <div className="video-message">
        Video is processing, check back later
      </div>;
    }

    if (videoHasError(video)) {
      return  <div className="video-message">
        Something went wrong :(
      </div>;
    }

    return <VideoPlayer
      video={video}
      useIframeForUSwitch={true}
    />;
  };

  render() {
    const { video, videoDetailUi, editable } = this.props;
    if (!video) {
      return null;
    }

    const formattedCreation = moment(video.created_at).format(MM_DD_YYYY);
    const collectionUrl = makeCollectionUrl(video.collection_key);
    return <div>
      <Toolbar onClickMenu={this.setDrawerOpen.bind(this, true)}>
        <img src="/static/images/mit_logo_grey_red.png" className="logo"/>
        <span className="title">
          ODL Video Services
        </span>
      </Toolbar>
      <Drawer open={videoDetailUi.drawerOpen} onDrawerClose={this.setDrawerOpen.bind(this, false)} />
      { video ? this.renderVideoPlayer(video) : null }
      <div className="summary">
        <p className="channelLink mdc-typography--subheading1">
          <a className="collection-link" href={collectionUrl}>
            {video.collection_title}
          </a>
        </p>
        <h2 className="video-title mdc-typography--title">
          {video.title}
        </h2>
        { video.description
          ?  <p className="video-description mdc-typography--body1">
            {video.description}
          </p>
          : null }
        <span className="upload-date mdc-typography--subheading1 fontgray">
          Uploaded {formattedCreation}
        </span>
        <span className="actions">
          <Button className="edit mdc-button--raised" onClick={this.openDialog} disabled={!editable}>
            <span className="material-icons">edit</span> Edit
          </Button>
          <Button className="share mdc-button--raised">
            <span className="material-icons">share</span> Share
          </Button>
        </span>
      </div>
      <Footer />
      <Dialog
        open={videoDetailUi.dialog.visible}
        onAccept={this.submitForm}
        onCancel={this.clearDialog}
        title="Edit video details"
      >
        <div className="mdc-form-field mdc-form-field--align-end">
          <Textfield
            label="New title:"
            id="video-title"
            onChange={this.setTitle}
            value={videoDetailUi.dialog.title}
          />
          <Textfield
            label="Description:"
            id="video-description"
            onChange={this.setDescription}
            value={videoDetailUi.dialog.description}
          />
        </div>
      </Dialog>
    </div>;
  }
}

const mapStateToProps = (state, ownProps) => {
  const { videoKey } = ownProps;
  const { videos, videoDetailUi } = state;
  const video = videos.data ? videos.data.get(videoKey) : null;
  const needsUpdate = !videos.processing && !videos.loaded;

  return {
    video,
    needsUpdate,
    videoDetailUi
  };
};

export default connect(mapStateToProps)(VideoDetailPage);
