// @flow
import R from 'ramda';
import _ from 'lodash';

export const PERM_CHOICE_NONE: string = 'none';
export const PERM_CHOICE_LISTS: string = 'lists';

export type DialogVisibilityState = {
  dialogVisibility: {
    [string]: boolean
  }
};

export const updateDialogVisibility = (state: DialogVisibilityState, dialogName: string, visible: boolean) => ({
  ...state,
  dialogVisibility: {
    ...state.dialogVisibility,
    [dialogName]: visible
  }
});

export const showDialog = R.partialRight(updateDialogVisibility, [true]);

export const hideDialog = R.partialRight(updateDialogVisibility, [false]);

export const updatedDialogState = (
  state: Object,
  dialogName: string,
  updateKey: string,
  updateValue: any
) => {
  let clonedState = _.cloneDeep(state);
  _.merge(clonedState.dialogs[dialogName], {[updateKey]: updateValue});
  return clonedState;
};

export const resetDialogState = (state: Object, dialogName: string, initialDialogState: Object) => {
  let clonedState = _.cloneDeep(state);
  clonedState.dialogs[dialogName] = initialDialogState;
  return clonedState;
};
