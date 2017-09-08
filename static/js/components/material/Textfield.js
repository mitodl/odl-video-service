// @flow
import React from 'react';

export default class Textfield extends React.Component {
  props: {
    id: string,
    label?: string,
    placeholder?: string
  };

  render() {
    const { label, id, ...otherProps } = this.props;

    let renderedLabel = label
      ? <label htmlFor={id}>{label}</label>
      : null;

    return <div className="mdc-textfield-container">
      { renderedLabel }
      <div className="mdc-textfield">
        <input type="text" className="mdc-textfield__input" id={id} {...otherProps} />
      </div>
    </div>;
  }
}
