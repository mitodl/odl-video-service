// @flow
/* global SETTINGS: false */
import React from 'react';
import { connect } from 'react-redux';
import type { Dispatch } from 'redux';
import R from 'ramda';
import _ from 'lodash';

import OVSToolbar from '../components/OVSToolbar';
import Footer from '../components/Footer';
import VideoCard from '../components/VideoCard';
import Drawer from '../components/material/Drawer';
import Button from "../components/material/Button";
import EditVideoFormDialog from '../components/dialogs/EditVideoFormDialog';
import ShareVideoDialog from '../components/dialogs/ShareVideoDialog';
import CollectionFormDialog from '../components/dialogs/CollectionFormDialog';
import { withDialogs } from '../components/dialogs/hoc';
import DropboxChooser from 'react-dropbox-chooser';

import { actions } from '../actions';
import * as commonUiActions from '../actions/commonUi';
import * as collectionUiActions from '../actions/collectionUi';
import { getActiveCollectionDetail } from '../lib/collection';
import { DIALOGS } from '../constants';

import type { Collection } from '../flow/collectionTypes';
import type { Video } from '../flow/videoTypes';
import type { CommonUiState } from "../reducers/commonUi";

class CollectionDetailPage extends React.Component {
  props: {
    dispatch: Dispatch,
    collection: ?Collection,
    collectionError: ?Object,
    collectionKey: string,
    editable: boolean,
    needsUpdate: boolean,
    commonUi: CommonUiState,
    showDialog: Function
  };

  componentDidMount() {
    this.updateRequirements();
  }

  componentDidUpdate() {
    if (!this.props.collectionError) {
      this.updateRequirements();
    }
  }

  updateRequirements = () => {
    const { dispatch, needsUpdate, collectionKey } = this.props;
    if (needsUpdate) {
      dispatch(actions.collections.get(collectionKey));
    }
  };

  showEditVideoDialog = (videoKey: string) => {
    const { dispatch, showDialog } = this.props;
    dispatch(collectionUiActions.setSelectedVideoKey(videoKey));
    showDialog(DIALOGS.EDIT_VIDEO);
  };

  showShareVideoDialog = (videoKey: string) => {
    const { dispatch, showDialog } = this.props;
    dispatch(collectionUiActions.setSelectedVideoKey(videoKey));
    showDialog(DIALOGS.SHARE_VIDEO);
  };

  setDrawerOpen = (open: boolean): void => {
    const { dispatch } = this.props;
    dispatch(commonUiActions.setDrawerOpen(open));
  };

  handleUpload = async (chosenFiles: Array<Object>) => {
    const { dispatch, collection } = this.props;
    if (!collection) throw "Collection does not exist";
    await dispatch(actions.uploadVideo.post(collection.key, chosenFiles));
    // Reload the collection after the video upload request succeeds
    dispatch(actions.collections.get(collection.key));
  };

  renderCollectionDescription = (description: ?string) => (
    !_.isEmpty(description)
      ? <p className="description">{ description }</p>
      : null
  );

  renderCollectionVideos = (videos: Array<Video>, isAdmin: boolean) => (
    videos.length > 0
      ? (
        <div className="videos">
          {videos.map(video => (
            <VideoCard
              video={video}
              key={video.key}
              isAdmin={isAdmin}
              showEditDialog={this.showEditVideoDialog.bind(this, video.key)}
              showShareDialog={this.showShareVideoDialog.bind(this, video.key)}
            />
          ), this)}
        </div>
      )
      : null
  );

  showEditCollectionDialog = (e: MouseEvent) => {
    const { dispatch, collection } = this.props;

    e.preventDefault();
    if (!collection) {
      // make flow happy
      throw new Error("Expected collection to exist");
    }

    dispatch(collectionUiActions.showEditCollectionDialog(collection));
  };

  renderBody(collection: Collection) {
    const videos = collection.videos || [];
    const collectionTitle = videos.length === 0
      ? collection.title
      : `${ collection.title } (${ videos.length })`;

    return <div className="centered-content">
      <header>
        <div className="text">
          <h2 className="mdc-typography--title">
            { collectionTitle }
          </h2>
        </div>
        <div className="tools">
          {
            collection.is_admin && [
              <a id="edit-collection-button" key="settings" onClick={ this.showEditCollectionDialog }>
                <i className="material-icons">settings</i>
              </a>,
              <DropboxChooser
                key="upload"
                appKey={SETTINGS.dropbox_key}
                success={this.handleUpload}
                linkType="direct"
                multiselect={true}
                extensions={['video']}
              >
                <Button className="dropbox-btn mdc-button--unelevated mdc-ripple-upgraded">
                  <img src="/static/images/dropbox_logo.png" alt="Dropbox Icon" />
                  Add Videos from Dropbox
                </Button>
              </DropboxChooser>
            ]
          }
        </div>
        { this.renderCollectionDescription(collection.description) }
      </header>
      { this.renderCollectionVideos(videos, collection.is_admin) }
    </div>;
  }

  renderError = (collectionError: Object) => {
    return <h2 className="mdc-typography--title error">
      { collectionError.detail }
    </h2>;
  };

  render() {
    const { collection, collectionError, commonUi } = this.props;

    if (!collection) return null;

    const detailBody = collectionError
      ? this.renderError(collectionError)
      : this.renderBody(collection);

    return <div>
      <OVSToolbar setDrawerOpen={this.setDrawerOpen.bind(this, true)} />
      <Drawer open={commonUi.drawerOpen} onDrawerClose={this.setDrawerOpen.bind(this, false)} />
      <div className="collection-detail-content">
        { detailBody }
      </div>
      <Footer />
    </div>;
  }
}

const mapStateToProps = (state, ownProps) => {
  const { match } = ownProps;
  const { collections, commonUi } = state;

  const collection = collections.loaded && collections.data ? collections.data : null;
  const collectionError = collections.error || null;
  const collectionKey = match.params.collectionKey;
  const activeCollection = getActiveCollectionDetail(state);
  const collectionChanged = activeCollection && activeCollection.key !== collectionKey;
  const needsUpdate = (!collections.processing && !collections.loaded) || collectionChanged;

  return {
    collectionKey,
    collection,
    collectionError,
    needsUpdate,
    commonUi
  };
};

export default R.compose(
  connect(mapStateToProps),
  withDialogs([
    {name: DIALOGS.COLLECTION_FORM, component: CollectionFormDialog},
    {name: DIALOGS.EDIT_VIDEO, component: EditVideoFormDialog},
    {name: DIALOGS.SHARE_VIDEO, component: ShareVideoDialog}
  ])
)(CollectionDetailPage);
