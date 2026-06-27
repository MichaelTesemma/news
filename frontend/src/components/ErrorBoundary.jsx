import { Component } from "react";
import { Link } from "react-router-dom";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error-boundary">
          <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 8v4M12 16h.01"/>
          </svg>
          <h2>Something went wrong</h2>
          <p>{this.state.error.message}</p>
          <div className="error-actions">
            <button onClick={() => window.location.reload()} className="btn-primary">
              Reload page
            </button>
            <Link to="/" className="btn-secondary">Go to feed</Link>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
