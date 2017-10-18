// @flow

export function getDisplayName(WrappedComponent: ReactClass<*>) {
  return WrappedComponent.displayName || WrappedComponent.name || 'Component';
}

/**
 * Returns a promise which resolves after a number of milliseconds have elapsed
 */
export const wait = (millis: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, millis));
