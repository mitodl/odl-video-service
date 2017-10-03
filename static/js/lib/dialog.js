// @flow
import R from 'ramda';

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
