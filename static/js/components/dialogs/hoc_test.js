import React from 'react';
import sinon from 'sinon';
import { assert } from 'chai';
import { mount } from 'enzyme';
import { Provider } from 'react-redux';
import configureTestStore from 'redux-asserts';
import R from 'ramda';

import rootReducer from '../../reducers';
import { INITIAL_UI_STATE } from '../../reducers/commonUi';
import { withDialogs } from './hoc';
import { SHOW_DIALOG } from '../../actions/commonUi';

describe('Dialog higher-order component', () => {
  let sandbox, store, listenForActions, dialogName;
  dialogName = 'TEST_DIALOG';

  class TestContainerPage extends React.Component {
    render() {
      return <div>
        <button id="open-btn" onClick={this.props.showDialog.bind(this, dialogName)}>Open Dialog</button>
      </div>;
    }
  }

  class TestDialog extends React.Component {
    render() {
      return <div>Fake Dialog</div>;
    }
  }

  const WrappedTestContainerPage = R.compose(
    withDialogs([
      {name: dialogName, component: TestDialog}
    ])
  )(TestContainerPage);

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    store = configureTestStore(rootReducer);
    listenForActions = store.createListenForActions();
  });

  afterEach(() => {
    sandbox.restore();
  });

  let renderTestComponentWithDialogs = () => (
    mount(
      <Provider store={store}>
        <WrappedTestContainerPage
          dispatch={store.dispatch}
          commonUi={{ ...INITIAL_UI_STATE, dialogVisibility: { [dialogName]: false }}}
        />
      </Provider>
    )
  );

  it('should render the specified dialogs with specific props', () => {
    let wrapper = renderTestComponentWithDialogs();
    let testDialog = wrapper.find('TestDialog');
    assert.isTrue(testDialog.exists());
    assert.isFalse(testDialog.props().open);
    assert.isFunction(testDialog.props().hideDialog);
  });

  it('should provide a function that lets the wrapped component launch the dialog', () => {
    let wrapper = renderTestComponentWithDialogs();
    return listenForActions([SHOW_DIALOG], () => {
      wrapper.find('#open-btn').simulate('click');
    }).then((state) => {
      assert.isTrue(state.commonUi.dialogVisibility[dialogName]);
    });
  });
});
