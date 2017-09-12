// @flow
import React from 'react';
import { connect } from 'react-redux';
import moment from 'moment';
import type { Dispatch } from "redux";
import R from 'ramda';

import Button from '../components/material/Button';
import Dialog from '../components/material/Dialog';
import Drawer from '../components/material/Drawer';
import OVSToolbar from '../components/OVSToolbar';
import Footer from '../components/Footer';
import VideoPlayer from '../components/VideoPlayer';
import Textfield from "../components/material/Textfield";
import Textarea from "../components/material/Textarea";
import EditVideoFormDialog from '../components/dialogs/EditVideoFormDialog';

import { actions } from '../actions';
import {
  setShareDialogVisibility,
  clearShareDialog
} from '../actions/videoDetailUi';
import { setDrawerOpen } from '../actions/commonUi';
import { withDialogs } from '../components/dialogs/hoc';
import { makeCollectionUrl, makeEmbedUrl } from '../lib/urls';
import { videoIsProcessing, videoHasError } from '../lib/video';
import { DIALOGS, MM_DD_YYYY } from '../constants';

import type { Video } from "../flow/videoTypes";
import type { VideoDetailUIState } from "../reducers/videoDetailUi";
import type { CommonUiState } from "../reducers/commonUi";

class VideoDetailPage extends React.Component {
  props: {
    dispatch: Dispatch,
    video: ?Video,
    videoKey: string,
    needsUpdate: boolean,
    videoDetailUi: VideoDetailUIState,
    commonUi: CommonUiState,
    showDialog: Function,
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

  openShareDialog = () => {
    const {dispatch} = this.props;
    dispatch(setShareDialogVisibility(true));
  };

  clearShareDialog = () => {
    const { dispatch } = this.props;
    dispatch(clearShareDialog());
  };

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
    const { video, videoDetailUi, commonUi, editable, showDialog } = this.props;
    if (!video) {
      return null;
    }
    const videoShareUrl = `${window.location.origin}${makeEmbedUrl(video.key)}`;
    const formattedCreation = moment(video.created_at).format(MM_DD_YYYY);
    const collectionUrl = makeCollectionUrl(video.collection_key);
    return <div>
      <OVSToolbar setDrawerOpen={this.setDrawerOpen.bind(this, true)} />
      <Drawer open={commonUi.drawerOpen} onDrawerClose={this.setDrawerOpen.bind(this, false)} />
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
          {
            editable &&
            <Button
              className="edit mdc-button--raised"
              onClick={showDialog.bind(this, DIALOGS.EDIT_VIDEO)}
              disabled={!editable}
            >
              <span className="material-icons">edit</span> Edit
            </Button>
          }
          <Button className="share mdc-button--raised"  onClick={this.openShareDialog}>
            <span className="material-icons">share</span> Share
          </Button>
        </span>
      </div>
      <Footer />
      <Dialog
        open={videoDetailUi.shareDialog.visible}
        title="Share this Video"
        onCancel={this.clearShareDialog}
        cancelText="Close"
        noSubmit={true}
        id="shareDialog"
      >
        <div className="mdc-form-field mdc-form-field--align-end">
          <Textfield
            readOnly
            label="Video URL"
            id="video-url"
            value={videoShareUrl}
          />
          <Textarea
            readOnly
            label="Embed HTML"
            id="video-embed-code"
            rows="4"
            value={`<iframe src="${videoShareUrl}" width="560" height="315" frameborder="0" allowfullscreen></iframe>`}
          />
        </div>
      </Dialog>
    </div>;
  }
}

const mapStateToProps = (state, ownProps) => {
  const { videoKey } = ownProps;
  const { videos, videoDetailUi, commonUi } = state;
  const video = videos.data ? videos.data.get(videoKey) : null;
  const needsUpdate = !videos.processing && !videos.loaded;

  return {
    video,
    needsUpdate,
    videoDetailUi,
    commonUi
  };
};

export default R.compose(
  connect(mapStateToProps),
  withDialogs([
    {name: DIALOGS.EDIT_VIDEO, component: EditVideoFormDialog}
  ])
)(VideoDetailPage);
