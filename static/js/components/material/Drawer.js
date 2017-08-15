// @flow
import React from 'react';
import { MDCTemporaryDrawer } from '@material/drawer/dist/mdc.drawer';

type DrawerProps = {
  open: boolean,
  onDrawerClose: () => void,
};

export default class Drawer extends React.Component {
  drawer: null;
  drawerRoot: null;

  props: DrawerProps;

  componentDidMount() {
    const { onDrawerClose } = this.props;
    this.drawer = new MDCTemporaryDrawer(this.drawerRoot);
    this.drawer.listen('MDCTemporaryDrawer:close', onDrawerClose);
  }

  componentWillUnmount() {
    if (this.drawer) {
      this.drawer.destroy();
    }
  }

  componentWillReceiveProps(nextProps: DrawerProps) {
    if (this.drawer) {
      if (this.props.open !== nextProps.open) {
        this.drawer.open = nextProps.open;
      }
    }
  }

  render() {
    return <aside className="mdc-temporary-drawer mdc-typography" ref={div => this.drawerRoot = div}>
      <nav className="mdc-temporary-drawer__drawer">
        <header className="mdc-temporary-drawer__header">
          <div className="mdc-temporary-drawer__header-content">
            Header here
          </div>
        </header>
        <nav id="icon-with-text-demo" className="mdc-temporary-drawer__content mdc-list">
          <a className="mdc-list-item mdc-temporary-drawer--selected" href="#">
            <i className="material-icons mdc-list-item__start-detail" aria-hidden="true">inbox</i>Inbox
          </a>
          <a className="mdc-list-item" href="#">
            <i className="material-icons mdc-list-item__start-detail" aria-hidden="true">star</i>Star
          </a>
        </nav>
      </nav>
    </aside>;
  }
}
