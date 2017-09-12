// @flow
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
import { setDrawerOpen } from '../actions/commonUi';
import { makeCollectionUrl } from '../lib/urls';
import { videoIsProcessing, videoHasError } from '../lib/video';
import { DIALOGS, MM_DD_YYYY } from '../constants';

import type { Video } from "../flow/videoTypes";
import type { CommonUiState } from "../reducers/commonUi";

class VideoDetailPage extends React.Component {
  props: {
    dispatch: Dispatch,
    video: ?Video,
    videoKey: string,
    needsUpdate: boolean,
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
    const { video, commonUi, editable, showDialog } = this.props;
    if (!video) {
      return null;
    }
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
          <Button
            className="share mdc-button--raised"
            onClick={showDialog.bind(this, DIALOGS.SHARE_VIDEO)}
          >
            <span className="material-icons">share</span> Share
          </Button>
        </span>
      </div>
      <Footer />
    </div>;
  }
}

const mapStateToProps = (state, ownProps) => {
  const { videoKey } = ownProps;
  const { videos, commonUi } = state;
  const video = videos.data ? videos.data.get(videoKey) : null;
  const needsUpdate = !videos.processing && !videos.loaded;

  return {
    video,
    needsUpdate,
    commonUi
  };
};

export default R.compose(
  connect(mapStateToProps),
  withDialogs([
    {name: DIALOGS.EDIT_VIDEO, component: EditVideoFormDialog},
    {name: DIALOGS.SHARE_VIDEO, component: ShareVideoDialog}
  ])
)(VideoDetailPage);
