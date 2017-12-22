// @flow

import {
  PERM_CHOICE_LISTS
} from "../lib/dialog";
import R from "ramda";

export function getDisplayName(WrappedComponent: ReactClass<*>) {
  return WrappedComponent.displayName || WrappedComponent.name || 'Component';
}

/**
 * Returns a promise which resolves after a number of milliseconds have elapsed
 */
export const wait = (millis: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, millis));

export const calculateListPermissionValue = (choice: string, listsInput: ?string): Array<string> => (
  choice !== PERM_CHOICE_LISTS || !listsInput || listsInput.trim().length === 0
    ? []
    : R.reject(R.isEmpty, R.map(R.trim, R.split(',', listsInput)))
);
