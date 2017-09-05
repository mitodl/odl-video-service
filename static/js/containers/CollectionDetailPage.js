// @flow
import React from 'react';
import { connect } from 'react-redux';
import type { Dispatch } from 'redux';
import _ from 'lodash';

import OVSToolbar from '../components/OVSToolbar';
import Footer from '../components/Footer';
import VideoCard from '../components/VideoCard';
import { actions } from '../actions';
import { getActiveCollectionDetail } from '../lib/collection';

import type { Collection } from '../flow/collectionTypes';
import type { Video } from '../flow/videoTypes';

class CollectionDetailPage extends React.Component {
  props: {
    dispatch: Dispatch,
    collection: ?Collection,
    collectionError: ?Object,
    collectionKey: string,
    editable: boolean,
    needsUpdate: boolean,
  };

  componentDidMount() {
    this.updateRequirements();
  }

  componentDidUpdate() {
    this.updateRequirements();
  }

  updateRequirements = () => {
    const { dispatch, needsUpdate, collectionKey } = this.props;
    if (needsUpdate) {
      dispatch(actions.collections.get(collectionKey));
    }
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
    const videos = collection.videos || [];
    const collectionTitle = videos.length === 0
      ? collection.title
      : `${ collection.title } (${ videos.length })`;

    return <div>
      <header>
        <h2 className="mdc-typography--title">
          { collectionTitle }
        </h2>
        { this.renderCollectionDescription(collection.description) }
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
    const { collection, collectionError } = this.props;

    if (!collection) return null;

    const detailBody = collectionError
      ? this.renderError(collectionError)
      : this.renderBody(collection);

    return <div>
      <OVSToolbar setDrawerOpen={() => {}} />
      <div className="collection-detail-content">
        { detailBody }
      </div>
      <Footer />
    </div>;
  }
}

const mapStateToProps = (state, ownProps) => {
  const { match } = ownProps;
  const { collections } = state;

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
    needsUpdate
  };
};

export default connect(mapStateToProps)(CollectionDetailPage);
