// @flow

export function getDisplayName(WrappedComponent: ReactClass<*>) {
  return WrappedComponent.displayName || WrappedComponent.name || 'Component';
}
