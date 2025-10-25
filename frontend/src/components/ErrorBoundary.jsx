import { Component } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

/**
 * Error Boundary Component
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
    };
  }

  static getDerivedStateFromError() {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details for debugging
    console.error('Error Boundary caught an error:', error, errorInfo);

    // Update state with error details
    this.setState((prevState) => ({
      error,
      errorInfo,
      errorCount: prevState.errorCount + 1,
    }));

    // You can also log the error to an error reporting service here
    // Example: logErrorToService(error, errorInfo);
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
    window.location.href = '/dashboard';
  };

  render() {
    if (this.state.hasError) {
      const { error, errorInfo, errorCount } = this.state;
      const isDevelopment = import.meta.env.DEV;

      return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black flex items-center justify-center p-4">
          <div className="max-w-2xl w-full">
            {/* Error Card */}
            <div className="bg-gray-800 rounded-2xl border border-red-500/30 shadow-2xl overflow-hidden">
              {/* Header */}
              <div className="bg-gradient-to-r from-red-500/20 to-orange-500/20 border-b border-red-500/30 p-6">
                <div className="flex items-center space-x-4">
                  <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center">
                    <AlertTriangle className="w-8 h-8 text-red-400" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-white mb-1">
                      Oops! Something went wrong
                    </h1>
                    <p className="text-gray-400 text-sm">
                      We encountered an unexpected error. Don't worry, your data is safe.
                    </p>
                  </div>
                </div>
              </div>

              {/* Error Details (Development Only) */}
              {isDevelopment && error && (
                <div className="p-6 border-b border-gray-700">
                  <h2 className="text-sm font-semibold text-red-400 mb-3">
                    Error Details (Development Mode)
                  </h2>
                  <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                    <p className="text-red-400 font-mono text-sm mb-2">
                      {error.toString()}
                    </p>
                    {errorInfo && (
                      <details className="mt-3">
                        <summary className="text-gray-400 text-xs cursor-pointer hover:text-white transition-colors">
                          Stack Trace
                        </summary>
                        <pre className="text-gray-500 text-xs mt-2 overflow-x-auto">
                          {errorInfo.componentStack}
                        </pre>
                      </details>
                    )}
                  </div>
                  {errorCount > 1 && (
                    <p className="text-yellow-400 text-xs mt-2">
                      ⚠️ This error has occurred {errorCount} times
                    </p>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="p-6">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {/* Try Again */}
                  <button
                    onClick={this.handleReset}
                    className="flex items-center justify-center space-x-2 bg-green-500 hover:bg-green-600 text-white px-4 py-3 rounded-lg font-semibold transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>Try Again</span>
                  </button>

                  {/* Reload Page */}
                  <button
                    onClick={this.handleReload}
                    className="flex items-center justify-center space-x-2 bg-gray-700 hover:bg-gray-600 text-white px-4 py-3 rounded-lg font-semibold transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>Reload Page</span>
                  </button>

                  {/* Go Home */}
                  <button
                    onClick={this.handleGoHome}
                    className="flex items-center justify-center space-x-2 bg-gray-700 hover:bg-gray-600 text-white px-4 py-3 rounded-lg font-semibold transition-colors"
                  >
                    <Home className="w-4 h-4" />
                    <span>Go Home</span>
                  </button>
                </div>

                {/* Help Text */}
                <div className="mt-6 p-4 bg-gray-900/50 rounded-lg border border-gray-700">
                  <h3 className="text-sm font-semibold text-white mb-2">
                    What can you do?
                  </h3>
                  <ul className="text-sm text-gray-400 space-y-1">
                    <li>• Click "Try Again" to attempt to recover</li>
                    <li>• Click "Reload Page" to refresh the entire application</li>
                    <li>• Click "Go Home" to return to the dashboard</li>
                    <li>• If the problem persists, please contact support</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="text-center mt-6">
              <p className="text-gray-500 text-sm">
                Error ID: {Date.now().toString(36).toUpperCase()}
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
