import { Component } from 'react';

export default class VizErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() { return { hasError: true }; }

  componentDidCatch(error) { console.warn('[VizErrorBoundary] Silenced:', error.message); }

  render() { return this.state.hasError ? null : this.props.children; }
}
