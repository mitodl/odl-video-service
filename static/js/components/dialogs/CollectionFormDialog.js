// @flow
import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import Radio from "../material/Radio"
import Textfield from "../material/Textfield"
import DescriptionField from "../material/DescriptionField"

import Dialog from "../material/Dialog"

import * as uiActions from "../../actions/collectionUi"
import { actions } from "../../actions"
import {
  PERM_CHOICE_NONE,
  PERM_CHOICE_LISTS,
  PERM_CHOICE_LOGGED_IN
} from "../../lib/dialog"
import { getCollectionForm } from "../../lib/collection"
import { DESCRIPTION_FORMAT_HTML } from "../../constants"
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
      users:                props.users || [],
      upgradingDescription: false,
      upgradeError:         null
    }
  }

  // Set on unmount so an upgrade that resolves afterwards does not setState on
  // a dead component.
  unmounted = false

  componentDidMount() {
    this.fetchPotentialCollectionOwners()
  }

  componentWillUnmount() {
    this.unmounted = true
  }

  /*
   * True when an in-flight upgrade no longer belongs to the form on screen.
   *
   * `upgradeDescription` awaits a PATCH, and onClose clears the form. By the
   * time the response arrives the dialog may have been closed, or reopened on a
   * different collection, and writing the old response into the current form
   * would show the author someone else's description.
   *
   * Only the *form* writes are skipped on a stale response. The button's own
   * "Converting…" state is cleared either way - it belongs to this component
   * rather than to the collection, and leaving it set would strand the field
   * the author is now looking at behind a disabled button.
   */
  isStaleUpgrade(key: ?string) {
    return this.props.collectionForm.key !== key
  }

  fetchPotentialCollectionOwners = async () => {
    const { dispatch } = this.props
    const { collectionKey } = this.props
    if (!collectionKey) {
      console.log("No collection key provided, skipping potential owner fetch.")
      return
    }
    try {
      const response = await dispatch(
        actions.potentialCollectionOwners.get(collectionKey)
      )
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

  // The rich-text editor hands back serialized HTML, not a DOM event.
  setCollectionDesc = (html: string) => {
    const { dispatch } = this.props
    dispatch(uiActions.setCollectionDesc(html))
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

  /**
   * Convert this collection's plain-text description to rich text.
   *
   * Saved on its own rather than folded into the dialog's save, so the author
   * gets the editor - with their words already in it - before deciding what to
   * write next. Whatever is in the textarea goes up with the request, so an
   * unsaved edit is converted rather than discarded.
   *
   * The server does the converting (ui.html.upgrade_description): it is the only
   * place that knows how to escape plain text and how to clean markup someone
   * once pasted into the old field.
   *
   * Only reachable for a saved collection. A collection being created starts as
   * rich text (see INITIAL_UI_STATE in reducers/collectionUi), because it has no
   * description written before rich text existed and so nothing to protect.
   *
   * Only the description comes back into the form. Re-seeding the whole form
   * from the response would discard every other unsaved edit in the dialog - the
   * PATCH sends the description alone, so the response still carries the *old*
   * title, and a title the author had just retyped would revert on the spot.
   */
  upgradeDescription = async () => {
    const { dispatch, collectionForm } = this.props

    const key = collectionForm.key
    this.setState({ upgradingDescription: true, upgradeError: null })
    try {
      const collection = await dispatch(
        actions.collections.patch(key, {
          description:        collectionForm.description,
          description_format: DESCRIPTION_FORMAT_HTML
        })
      )
      if (this.unmounted) {
        return
      }
      this.setState({ upgradingDescription: false })
      if (this.isStaleUpgrade(key)) {
        return
      }
      dispatch(uiActions.setCollectionDesc(collection.description))
      dispatch(uiActions.setCollectionDescFormat(collection.description_format))
    } catch (error) {
      if (this.unmounted) {
        return
      }
      this.setState({
        upgradingDescription: false,
        // Not this form's error to report once the dialog has moved on.
        upgradeError:         this.isStaleUpgrade(key) ?
          null :
          "That description could not be converted. Please try again."
      })
    }
  }

  submitForm = async () => {
    if (this.state.upgradingDescription) {
      return
    }
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
    /*
     * Only on create, where this request is what decides the new row's format.
     *
     * On an update it is server-owned state: only the explicit upgrade changes
     * it, and the API accepts an html -> text downgrade, so re-asserting the
     * form's copy would let a second tab or the Django admin be overwritten by
     * whatever this page last read - leaving markup stored as plain text and
     * rendered escaped. Omitted, the serializer keeps the stored format.
     */
    if (isNew) {
      payload.description_format = collectionForm.description_format
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
          <DescriptionField
            label="Description (optional)"
            id="collection-desc"
            placeholder="Add a description, links or next steps for learners."
            onChange={this.setCollectionDesc}
            value={collectionForm.description || ""}
            descriptionFormat={collectionForm.description_format}
            onUpgrade={this.upgradeDescription}
            upgrading={this.state.upgradingDescription}
            upgradeError={this.state.upgradeError}
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
