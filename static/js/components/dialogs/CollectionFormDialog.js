// @flow
import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import Radio from "../material/Radio"
import Textfield from "../material/Textfield"
import Textarea from "../material/Textarea"

import Dialog from "../material/Dialog"

import * as uiActions from "../../actions/collectionUi"
import { actions } from "../../actions"
import {
  PERM_CHOICE_NONE,
  PERM_CHOICE_LISTS,
  PERM_CHOICE_LOGGED_IN
} from "../../lib/dialog"
import { getCollectionForm } from "../../lib/collection"
import { makeCollectionUrl } from "../../lib/urls"
import { calculateListPermissionValue } from "../../util/util"
import {
  setCollectionFormErrors,
  clearCollectionErrors
} from "../../actions/collectionUi"

import type {
  CollectionFormState,
  CollectionUiState,
  Collection
} from "../../flow/collectionTypes"

type DialogProps = {
  dispatch: Dispatch,
  history: Object,
  collectionUi: CollectionUiState,
  collection: ?Collection,
  collectionForm: CollectionFormState,
  open: boolean,
  hideDialog: Function,
  isEdxCourseAdmin?: boolean
}

export class CollectionFormDialog extends React.Component<*, void> {
  props: DialogProps

  constructor(props) {
    super(props)
    this.state = {
      users: props.users || []
    }
  }

  componentDidMount() {
    this.fetchPotentialCollectionOwners()
  }

  fetchPotentialCollectionOwners = async () => {
    const { dispatch } = this.props
    try {
      const { collectionKey } = this.props
      const response = await dispatch(actions.potentialCollectionOwners.get(collectionKey))
      this.setState({ users: response.users || [] })
    } catch (error) {
      console.error("Error fetching users:", error)
      this.handleError(error)
    }
  }

  setCollectionTitle = (event: Object) => {
    const { dispatch } = this.props
    dispatch(uiActions.setCollectionTitle(event.target.value))
  }

  setCollectionDesc = (event: Object) => {
    const { dispatch } = this.props
    dispatch(uiActions.setCollectionDesc(event.target.value))
  }

  setCollectionViewPermChoice = (choice: string) => {
    const { dispatch, collectionForm } = this.props
    if (choice !== collectionForm.viewChoice) {
      dispatch(uiActions.setViewChoice(choice))
    }
  }

  setCollectionAdminPermChoice = (choice: string) => {
    const { dispatch, collectionForm } = this.props
    if (choice !== collectionForm.adminChoice) {
      dispatch(uiActions.setAdminChoice(choice))
    }
  }

  handleCollectionViewPermClick = (event: Object) => {
    this.setCollectionViewPermChoice(event.target.value)
  }

  handleCollectionAdminPermClick = (event: Object) => {
    this.setCollectionAdminPermChoice(event.target.value)
  }

  setCollectionViewPermLists = (event: Object) => {
    const { dispatch } = this.props
    dispatch(uiActions.setViewLists(event.target.value))
  }

  setCollectionAdminPermLists = (event: Object) => {
    const { dispatch } = this.props
    dispatch(uiActions.setAdminLists(event.target.value))
  }

  setCollectionEdxCourseId = (event: Object) => {
    const { dispatch } = this.props
    dispatch(uiActions.setEdxCourseId(event.target.value))
  }

  setCollectionOwner = (event: Object) => {
    const { dispatch } = this.props
    dispatch(uiActions.setOwnerId(parseInt(event.target.value, 10)))
  }

  submitForm = async () => {
    const {
      dispatch,
      history,
      collectionUi: { isNew },
      collectionForm,
      isEdxCourseAdmin
    } = this.props

    const payload: Object = {
      title:       collectionForm.title,
      description: collectionForm.description,
      view_lists:  calculateListPermissionValue(
        collectionForm.viewChoice,
        collectionForm.viewLists
      ),
      admin_lists: calculateListPermissionValue(
        collectionForm.adminChoice,
        collectionForm.adminLists
      ),
      is_logged_in_only: collectionForm.viewChoice === PERM_CHOICE_LOGGED_IN
    }
    if (isEdxCourseAdmin) {
      payload.edx_course_id = collectionForm.edxCourseId
    }
    if (collectionForm.ownerId) {
      payload.owner = collectionForm.ownerId
    }

    try {
      if (isNew) {
        const collection = await dispatch(actions.collectionsList.post(payload))
        history.push(makeCollectionUrl(collection.key))
        this.addToastMessage({
          message: {
            key:     "collection-created",
            content: "Collection created",
            icon:    "check"
          }
        })
      } else {
        await dispatch(actions.collections.patch(collectionForm.key, payload))
        this.addToastMessage({
          message: {
            key:     "collection-updated",
            content: "Changes saved",
            icon:    "check"
          }
        })
      }
      dispatch(actions.collectionsList.get())
      this.onClose()
    } catch (e) {
      this.handleError(e)
    }
  }

  addToastMessage(...args: any[]) {
    this.props.dispatch(actions.toast.addMessage(...args))
  }

  onClose = () => {
    const { dispatch, hideDialog } = this.props
    dispatch(uiActions.clearCollectionForm())
    hideDialog()
  }

  handleError = (error: Error) => {
    const { dispatch, collectionForm } = this.props
    dispatch(
      setCollectionFormErrors({
        ...collectionForm,
        errors: error
      })
    )
    dispatch(clearCollectionErrors())
  }

  render() {
    const {
      open,
      hideDialog,
      collectionForm,
      collectionUi: { isNew, errors },
      isEdxCourseAdmin
    } = this.props

    const title = isNew ? "Create a New Collection" : "Edit Collection"
    const submitText = isNew ? "Create Collection" : "Save"

    return (
      <Dialog
        id="ovs-form-dialog"
        title={title}
        cancelText="Cancel"
        submitText={submitText}
        hideDialog={hideDialog}
        onAccept={this.submitForm}
        onCancel={this.onClose}
        open={open}
        validateOnClick={true}
      >
        <div className="ovs-form-dialog">
          <Textfield
            label="Collection Title"
            id="collection-title"
            onChange={this.setCollectionTitle}
            value={collectionForm.title || ""}
            required={true}
            minLength={1}
            validationMessage={errors ? errors.title : ""}
          />
          <Textarea
            label="Description (optional)"
            id="collection-desc"
            rows="4"
            onChange={this.setCollectionDesc}
            value={collectionForm.description || ""}
          />

          <section className="permission-group">
            <h4>Who can view videos?</h4>
            <Radio
              id="view-only-me"
              label="Only owner"
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
                onFocus={this.setCollectionViewPermChoice.bind(
                  this,
                  PERM_CHOICE_LISTS
                )}
                value={collectionForm.viewLists || ""}
                validationMessage={errors ? errors.view_lists : ""}
              />
            </Radio>
            <Radio
              id="view-logged-in-only"
              label="MIT Touchstone"
              radioGroupName="view-perms"
              value={PERM_CHOICE_LOGGED_IN}
              selectedValue={collectionForm.viewChoice}
              onChange={this.handleCollectionViewPermClick}
            />
          </section>

          <section className="permission-group">
            <h4>Who can upload/edit videos?</h4>
            <Radio
              id="admin-only-me"
              label="Only owner"
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
                onFocus={this.setCollectionAdminPermChoice.bind(
                  this,
                  PERM_CHOICE_LISTS
                )}
                value={collectionForm.adminLists || ""}
                validationMessage={errors ? errors.admin_lists : ""}
              />
            </Radio>
          </section>

          {!!isEdxCourseAdmin && (
            <Textfield
              label="edx Course ID"
              id="edx-course-id"
              onChange={this.setCollectionEdxCourseId}
              value={collectionForm.edxCourseId || ""}
              required={false}
              validationMessage={errors ? errors.edx_course_id : ""}
            />
          )}
          <div className="owner-selection">
            <label htmlFor="collection-owner">Owner</label>
            <select
              id="collection-owner"
              onChange={this.setCollectionOwner}
              value={collectionForm.ownerId || ""}
            >
              {this.state.users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.username} {user.email && `(${user.email})`}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Dialog>
    )
  }
}

export const mapStateToProps = (state: any) => {
  const { collectionUi } = state

  const collectionForm = getCollectionForm(collectionUi)
  return {
    collectionUi,
    collectionForm
  }
}

const ConnectedCollectionFormDialog = connect(mapStateToProps)(
  CollectionFormDialog
)
export default ConnectedCollectionFormDialog
