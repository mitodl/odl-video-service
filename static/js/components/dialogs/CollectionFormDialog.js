// @flow
import React from 'react';
import { connect } from 'react-redux';
import type { Dispatch } from 'redux';
import R from 'ramda';
import _ from 'lodash';

import Radio from "../material/Radio";
import Dialog from "../material/Dialog";
import Textfield from "../material/Textfield";
import Textarea from "../material/Textarea";

import * as uiActions from '../../actions/collectionUi';
import { actions } from '../../actions';
import { PERM_CHOICE_NONE, PERM_CHOICE_LISTS } from '../../lib/dialog';

import type { CollectionUiState } from "../../reducers/collectionUi";
import type { Collection } from '../../flow/collectionTypes';

type DialogProps = {
  dispatch: Dispatch,
  collectionUi: CollectionUiState,
  collection: ?Collection,
  open: boolean,
  hideDialog: Function,
}

class CollectionFormDialog extends React.Component {
  props: DialogProps;

  componentDidMount() {
    this.checkCollectionForm();
  }

  componentDidUpdate() {
    this.checkCollectionForm();
  }

  checkCollectionForm() {
    const {
      open,
      collection,
      collectionUi: { collectionForm }
    } = this.props;
    if (open && collection && collection.key !== collectionForm.key) {
      this.initializeFormWithCollection(collection);
    }
  }

  initializeFormWithCollection(collection: Collection) {
    const { dispatch } = this.props;

    let viewChoice = collection.view_lists.length === 0
      ? PERM_CHOICE_NONE
      : PERM_CHOICE_LISTS;
    let adminChoice = collection.admin_lists.length === 0
      ? PERM_CHOICE_NONE
      : PERM_CHOICE_LISTS;
    dispatch(uiActions.initCollectionForm({
      key: collection.key,
      title: collection.title,
      description: collection.description,
      viewChoice: viewChoice,
      viewLists: _.join(collection.view_lists, ','),
      adminChoice: adminChoice,
      adminLists: _.join(collection.admin_lists, ',')
    }));
  }

  setCollectionTitle = (event: Object) => {
    const { dispatch } = this.props;
    dispatch(uiActions.setCollectionTitle(event.target.value));
  };

  setCollectionDesc = (event: Object) => {
    const { dispatch } = this.props;
    dispatch(uiActions.setCollectionDesc(event.target.value));
  };

  setCollectionViewPermChoice = (choice: string) => {
    const { dispatch, collectionUi: { collectionForm } } = this.props;
    if (choice !== collectionForm.viewChoice) {
      dispatch(uiActions.setViewChoice(choice));
    }
  };

  setCollectionAdminPermChoice = (choice: string) => {
    const { dispatch, collectionUi: { collectionForm } } = this.props;
    if (choice !== collectionForm.adminChoice) {
      dispatch(uiActions.setAdminChoice(choice));
    }
  };

  handleCollectionViewPermClick = (event: Object) => {
    this.setCollectionViewPermChoice(event.target.value);
  };

  handleCollectionAdminPermClick = (event: Object) => {
    this.setCollectionAdminPermChoice(event.target.value);
  };

  setCollectionViewPermLists = (event: Object) => {
    const { dispatch } = this.props;
    dispatch(uiActions.setViewLists(event.target.value));
  };

  setCollectionAdminPermLists = (event: Object) => {
    const { dispatch } = this.props;
    dispatch(uiActions.setAdminLists(event.target.value));
  };

  submitForm = () => {
    const {
      dispatch,
      hideDialog,
      collectionUi: { collectionForm }
    } = this.props;

    let patchData = {
      title: collectionForm.title,
      description: collectionForm.description,
      view_lists: this.calculateListPermissionValue(collectionForm.viewChoice, collectionForm.viewLists),
      admin_lists: this.calculateListPermissionValue(collectionForm.adminChoice, collectionForm.adminLists)
    };
    dispatch(actions.collections.patch(collectionForm.key, patchData)).then(
      (collection) => {
        hideDialog();
        this.initializeFormWithCollection(collection);
      }
    );
  };

  calculateListPermissionValue = (choice: string, listsInput: ?string): Array<string> => (
    choice === PERM_CHOICE_NONE || !listsInput || listsInput.trim().length === 0
      ? []
      : R.map(R.trim, R.split(',', listsInput))
  );

  render() {
    const {
      open,
      hideDialog,
      collection,
      collectionUi: { collectionForm }
    } = this.props;

    let title = collection ? "Edit Collection" : "Create a New Collection";
    let submitText = collection ? "Save Changes" : "Create Collection";

    return (
      <Dialog
        id="collection-form-dialog"
        title={title}
        cancelText="Cancel"
        submitText={submitText}
        onCancel={hideDialog}
        onAccept={this.submitForm}
        open={open}
      >
        <div className="collection-form-dialog">
          <Textfield
            label="Collection Title"
            id="collection-title"
            onChange={this.setCollectionTitle}
            value={collectionForm.title || ''}
          />
          <Textarea
            label="Description (optional)"
            id="collection-desc"
            rows="4"
            onChange={this.setCollectionDesc}
            value={collectionForm.description || ''}
          />

          <section className="permission-group">
            <h4>Who can view videos?</h4>
            <Radio
              id="view-only-me"
              label="Only me"
              radioGroupName="view-perms"
              value={PERM_CHOICE_NONE}
              selectedValue={collectionForm.viewChoice}
              onChange={this.handleCollectionViewPermClick}
            />
            <Radio
              id="view-moira"
              label="Moira Lists"
              radioGroupName="view-perms"
              value={PERM_CHOICE_LISTS}
              selectedValue={collectionForm.viewChoice}
              onChange={this.handleCollectionViewPermClick}
            >
              <Textfield
                id="view-moira-input"
                placeholder="Add Moira list(s), separated by commas"
                onChange={this.setCollectionViewPermLists}
                onFocus={this.setCollectionViewPermChoice.bind(this, PERM_CHOICE_LISTS)}
                value={collectionForm.viewLists || ''}
              />
            </Radio>
          </section>

          <section className="permission-group">
            <h4>Who can upload/edit videos?</h4>
            <Radio
              id="admin-only-me"
              label="Only me"
              radioGroupName="admin-perms"
              value={PERM_CHOICE_NONE}
              selectedValue={collectionForm.adminChoice}
              onChange={this.handleCollectionAdminPermClick}
            />
            <Radio
              id="admin-moira"
              label="Moira Lists"
              radioGroupName="admin-perms"
              value={PERM_CHOICE_LISTS}
              selectedValue={collectionForm.adminChoice}
              onChange={this.handleCollectionAdminPermClick}
            >
              <Textfield
                id="admin-moira-input"
                placeholder="Add Moira list(s), separated by commas"
                onChange={this.setCollectionAdminPermLists}
                onFocus={this.setCollectionAdminPermChoice.bind(this, PERM_CHOICE_LISTS)}
                value={collectionForm.adminLists || ''}
              />
            </Radio>
          </section>
        </div>
      </Dialog>
    );
  }
}

const mapStateToProps = (state) => {
  const { collectionUi } = state;

  return {
    collectionUi
  };
};

export default connect(mapStateToProps)(CollectionFormDialog);
