// @flow
/* global SETTINGS: false */
import React from 'react';
import { connect } from 'react-redux';
import moment from 'moment';
import type { Dispatch } from "redux";
import R from 'ramda';

import Button from '../components/material/Button';
import Drawer from '../components/material/Drawer';
import OVSToolbar from '../components/OVSToolbar';
import Footer from '../components/Footer';
import VideoPlayer from '../components/VideoPlayer';
import EditVideoFormDialog from '../components/dialogs/EditVideoFormDialog';
import ShareVideoDialog from '../components/dialogs/ShareVideoDialog';
import { withDialogs } from '../components/dialogs/hoc';

import { actions } from '../actions';
import * as videoSubtitleActions from '../actions/videoUi';
import { setDrawerOpen } from '../actions/commonUi';
import { makeCollectionUrl } from '../lib/urls';
import { saveToDropbox } from '../lib/video';
import { videoIsProcessing, videoHasError } from '../lib/video';
import { DIALOGS, MM_DD_YYYY } from '../constants';

import type { Video } from "../flow/videoTypes";
import type { CommonUiState } from "../reducers/commonUi";
import type { VideoUiState } from "../reducers/videoUi";
import VideoSubtitleCard from "../components/VideoSubtitleCard";
import { updateVideoJsSync } from "../actions/videoUi";
import { initGA, sendGAPageView } from "../util/google_analytics";
import VideoSaverScript from "../components/VideoSaverScript";

class VideoDetailPage extends React.Component {
  props: {
    dispatch: Dispatch,
    video: ?Video,
    videoKey: string,
    needsUpdate: boolean,
    commonUi: CommonUiState,
    videoUi: VideoUiState,
    showDialog: Function,
    editable: boolean
  };

  componentDidMount() {
    this.updateRequirements();
    initGA();
    sendGAPageView(window.location.pathname);
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

  setDrawerOpen = (open: boolean): void => {
    const { dispatch } = this.props;
    dispatch(setDrawerOpen(open));
  };

  deleteSubtitle = async (videoSubtitleId) => {
    const {
      dispatch,
      videoKey
    } = this.props;
    await dispatch(actions.videoSubtitles.delete(videoSubtitleId));
    dispatch(actions.videos.get(videoKey));
  };

  uploadVideoSubtitle = async () => {
    const {
      dispatch,
      video,
      videoKey,
      videoUi: {videoSubtitleForm}
    } = this.props;
    if (video && videoSubtitleForm.subtitle) {
      const formData = new FormData();
      formData.append('file', videoSubtitleForm.subtitle);
      formData.append('collection', video.collection_key);
      formData.append('video', video.key);
      formData.append('language', videoSubtitleForm.language);
      // $FlowFixMe: A file always has a name
      formData.append('filename', videoSubtitleForm.subtitle.name);
      await dispatch(actions.videoSubtitles.post(formData));
      dispatch(actions.videos.get(videoKey));
    }
  };

  setUploadSubtitle = async (event: Object) => {
    const { dispatch } = this.props;
    await dispatch(videoSubtitleActions.setUploadSubtitle(event.target.files[0]));
    this.uploadVideoSubtitle();
  };

  updateCorner = (corner: string) => {
    const { dispatch } = this.props;
    dispatch(updateVideoJsSync(corner));
  };

  renderVideoPlayer = (video: Video) => {
    const { videoUi } = this.props;
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
      cornerFunc={this.updateCorner}
      selectedCorner={videoUi.corner}
    />;
  };

  render() {
    const { video, commonUi, editable, showDialog } = this.props;
    if (!video) {
      return null;
    }
    const formattedCreation = moment(video.created_at).format(MM_DD_YYYY);
    const collectionUrl = makeCollectionUrl(video.collection_key);
    return <div>
      <VideoSaverScript />
      <OVSToolbar setDrawerOpen={this.setDrawerOpen.bind(this, true)} />
      <Drawer open={commonUi.drawerOpen} onDrawerClose={this.setDrawerOpen.bind(this, false)} />
      { video ? this.renderVideoPlayer(video) : null }
      <div className="mdc-layout-grid mdc-video-detail">
        <div className="mdc-layout-grid__inner">
          <div className="summary mdc-layout-grid__cell--span-7">
            <div className="card video-summary-card">
              <p className="channelLink mdc-typography--subheading1">
                <a className="collection-link" href={collectionUrl}>
                  {video.collection_title}
                </a>
              </p>
              <h2 className="video-title mdc-typography--title">
                {video.title}
              </h2>
              <div className="actions">
                <Button
                  className="share mdc-button--raised"
                  onClick={showDialog.bind(this, DIALOGS.SHARE_VIDEO)}
                >
                  <span className="material-icons ">share</span> Share
                </Button>
                {
                  editable &&
                  <span>
                    <Button
                      className="edit mdc-button--raised"
                      onClick={showDialog.bind(this, DIALOGS.EDIT_VIDEO)}
                    >
                      <span className="material-icons">edit</span> Edit
                    </Button>
                    <Button
                      className="dropbox mdc-button--raised"
                      onClick={saveToDropbox.bind(this, video)}
                    >
                      <span className="material-icons ">file_download</span> Save To Dropbox
                    </Button>
                  </span>
                }
              </div>
              { video.description &&
              <p
                className="video-description mdc-typography--body1"
              >
                {video.description}
              </p>
              }
              <div className="upload-date mdc-typography--subheading1 fontgray">
                Uploaded {formattedCreation}
              </div>
            </div>
          </div>
          <div className="video-subtitles mdc-layout-grid__cell--span-5">
            <VideoSubtitleCard
              id="subtitleCard"
              video={video} isAdmin={editable}
              uploadVideoSubtitle={this.setUploadSubtitle}
              deleteVideoSubtitle={this.deleteSubtitle}
            />
          </div>
        </div>
      </div>
      <Footer />
    </div>;
  }
}

const mapStateToProps = (state, ownProps) => {
  const { videoKey } = ownProps;
  const { videos, commonUi, videoUi } = state;
  const video = videos.data ? videos.data.get(videoKey) : null;
  const needsUpdate = !videos.processing && !videos.loaded;

  return {
    video,
    needsUpdate,
    commonUi,
    videoUi
  };
};

export default R.compose(
  connect(mapStateToProps),
  withDialogs([
    {name: DIALOGS.EDIT_VIDEO, component: EditVideoFormDialog},
    {name: DIALOGS.SHARE_VIDEO, component: ShareVideoDialog}
  ])
)(VideoDetailPage);
