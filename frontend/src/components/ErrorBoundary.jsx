import { Component } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
      globalErrors: [],
    };
    this._globalHandlers = [];
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidMount() {
    this._attachGlobalHandlers();
  }

  componentWillUnmount() {
    this._detachGlobalHandlers();
  }

  _attachGlobalHandlers() {
    const onUnhandledRejection = (event) => {
      const error = event.reason;
      console.error('Global unhandled promise rejection:', error);

      if (this.props.onError) {
        this.props.onError(error, 'unhandledrejection');
      }

      this.setState((prevState) => ({
        errorCount: prevState.errorCount + 1,
        globalErrors: [...prevState.globalErrors, { error, type: 'unhandledrejection', time: Date.now() }],
      }));
    };

    const onRuntimeError = (event) => {
      const error = event.error || new Error(event.message);
      console.error('Global runtime error:', error);

      if (this.props.onError) {
        this.props.onError(error, 'error');
      }

      this.setState((prevState) => ({
        errorCount: prevState.errorCount + 1,
        globalErrors: [...prevState.globalErrors, { error, type: 'runtime', time: Date.now() }],
      }));
    };

    window.addEventListener('unhandledrejection', onUnhandledRejection);
    window.addEventListener('error', onRuntimeError);
    this._globalHandlers = [
      { type: 'unhandledrejection', handler: onUnhandledRejection },
      { type: 'error', handler: onRuntimeError },
    ];
  }

  _detachGlobalHandlers() {
    for (const { type, handler } of this._globalHandlers) {
      window.removeEventListener(type, handler);
    }
    this._globalHandlers = [];
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error Boundary caught an error:', error, errorInfo);

    this.setState((prevState) => ({
      error,
      errorInfo,
      errorCount: prevState.errorCount + 1,
    }));

    if (this.props.onError) {
      this.props.onError(error, 'react-boundary', errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const { error, errorInfo, errorCount, globalErrors } = this.state;
      const isDevelopment = import.meta.env.DEV;
      const errorId = Date.now().toString(36).toUpperCase();
      const recentGlobalErrors = globalErrors.filter(e => Date.now() - e.time < 60000);

      return (
        <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "var(--color-surface)" }}>
          <div className="max-w-2xl w-full">
            <div className="bg-card rounded-2xl border border-red-500/30 shadow-2xl overflow-hidden">
              <div className="bg-gradient-to-r from-red-500/20 to-orange-500/20 border-b border-red-500/30 p-6">
                <div className="flex items-center space-x-4">
                  <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center">
                    <AlertTriangle className="w-8 h-8 text-red-700" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-normal text-heritage-ink mb-1">
                      Oops! Something went wrong
                    </h1>
                    <p className="text-heritage-muted text-sm">
                      We encountered an unexpected error. Retry or return home.
                    </p>
                  </div>
                </div>
              </div>

              {isDevelopment && error && (
                <div className="p-6 border-b border-gray-700">
                  <h2 className="text-sm font-semibold text-red-700 mb-3">
                    Error Details (Development Mode)
                  </h2>
                  <div className="bg-card-hover rounded-lg p-4 border border-card-border">
                    <p className="text-red-700 font-mono text-sm mb-2">
                      {error.toString()}
                    </p>
                    {errorInfo && (
                      <details className="mt-3">
                        <summary className="text-heritage-muted text-xs cursor-pointer hover:text-heritage-ink transition-colors">
                          Stack Trace
                        </summary>
                        <pre className="text-heritage-muted text-xs mt-2 overflow-x-auto max-h-48">
                          {errorInfo.componentStack}
                        </pre>
                      </details>
                    )}
                  </div>
                  {errorCount > 1 && (
                    <p className="text-yellow-400 text-xs mt-2">
                      This error has occurred {errorCount} times
                    </p>
                  )}
                </div>
              )}

              {isDevelopment && recentGlobalErrors.length > 0 && (
                <div className="p-6 border-b border-gray-700">
                  <h2 className="text-sm font-semibold text-orange-400 mb-3 flex items-center gap-2">
                    <Bug className="w-4 h-4" />
                    Global Errors ({recentGlobalErrors.length} in last 60s)
                  </h2>
                  <div className="space-y-2">
                    {recentGlobalErrors.slice(0, 5).map((ge, i) => (
                      <div key={i} className="bg-card-hover rounded-lg p-3 border border-card-border">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-mono text-heritage-muted">
                            {ge.type === 'unhandledrejection' ? 'Promise' : 'Runtime'}
                          </span>
                          <span className="text-xs text-heritage-muted">
                            {new Date(ge.time).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-orange-300 font-mono text-xs break-all">
                          {ge.error?.message || ge.error?.toString() || 'Unknown'}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="p-6">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <button
                    onClick={this.handleReset}
                    className="flex items-center justify-center space-x-2 bg-heritage hover:bg-green-800 text-white px-4 py-3 rounded-lg font-semibold transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>Try Again</span>
                  </button>

                  <button
                    onClick={this.handleReload}
                    className="flex items-center justify-center space-x-2 bg-card-hover hover:bg-surface text-heritage-ink px-4 py-3 rounded-lg font-semibold transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>Reload Page</span>
                  </button>

                  <button
                    onClick={this.handleGoHome}
                    className="flex items-center justify-center space-x-2 bg-card-hover hover:bg-surface text-heritage-ink px-4 py-3 rounded-lg font-semibold transition-colors"
                  >
                    <Home className="w-4 h-4" />
                    <span>Go Home</span>
                  </button>
                </div>

                <div className="mt-6 p-4 bg-card-hover rounded-lg border border-card-border">
                  <h3 className="text-sm font-semibold text-heritage-ink mb-2">
                    What can you do?
                  </h3>
                  <ul className="text-sm text-heritage-muted space-y-1">
                    <li>Click "Try Again" to attempt to recover</li>
                    <li>Click "Reload Page" to refresh the entire application</li>
                    <li>Click "Go Home" to return to the dashboard</li>
                    <li>If the problem persists, please contact support</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="text-center mt-6">
              <p className="text-heritage-muted text-sm">
                Error ID: {errorId}
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
