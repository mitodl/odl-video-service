// @flow
import React from 'react';

export default class Textfield extends React.Component {
  props: {
    label: string,
    id: string,
  };

  render() {
    const { label, id, ...otherProps } = this.props;

    return <span>
      <label htmlFor={id}>{label}</label>
      <div className="mdc-textfield">
        <input type="text" className="mdc-textfield__input" id={id} {...otherProps} />
      </div>
    </span>;
  }
}
