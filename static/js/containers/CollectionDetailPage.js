// @flow
import React from 'react';
import { connect } from 'react-redux';
import type { Dispatch } from 'redux';
import R from 'ramda';
import _ from 'lodash';

import OVSToolbar from '../components/OVSToolbar';
import Footer from '../components/Footer';
import VideoCard from '../components/VideoCard';
import Drawer from '../components/material/Drawer';
import NewCollection from '../components/dialogs/CollectionFormDialog';
import { withDialogs } from '../components/dialogs/hoc';

import { actions } from '../actions';
import { setDrawerOpen } from '../actions/commonUi';
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

  setDrawerOpen = (open: boolean): void => {
    const { dispatch } = this.props;
    dispatch(setDrawerOpen(open));
  };

  renderCollectionDescription = (description: ?string) => (
    !_.isEmpty(description)
      ? <p className="description">{ description }</p>
      : null
  );

  renderCollectionVideos = (videos: Array<Video>) => (
    videos.length > 0
      ? (
        <div className="videos">
          {videos.map(video => (
            <VideoCard video={video} key={video.key} />
          ))}
        </div>
      )
      : null
  );

  renderBody(collection: Collection) {
    const { showDialog } = this.props;

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
          { this.renderCollectionDescription(collection.description) }
        </div>
        <div className="tools">
          {
            collection.is_admin &&
            <a onClick={ showDialog.bind(this, DIALOGS.NEW_COLLECTION) }>
              <i className="material-icons">settings</i>
            </a>
          }
        </div>
      </header>
      { this.renderCollectionVideos(videos) }
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
    {name: DIALOGS.NEW_COLLECTION, component: NewCollection}
  ])
)(CollectionDetailPage);
