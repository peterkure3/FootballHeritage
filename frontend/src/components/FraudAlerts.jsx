import { useState } from 'react';
import { AlertTriangle, Eye, CheckCircle, X, Shield, TrendingUp, Users, DollarSign } from 'lucide-react';
import { toast } from 'react-hot-toast';

/**
 * Fraud Alerts Dashboard Component
 * Displays suspicious activities and fraud detection alerts
 */

const FraudAlerts = () => {
  const [alerts, setAlerts] = useState([
    {
      id: 1,
      type: 'multiple_accounts',
      severity: 'high',
      user_email: 'suspicious1@example.com',
      user_id: 'uuid-1',
      description: 'Multiple accounts detected from same IP address',
      details: {
        ip_address: '192.168.1.100',
        accounts_count: 5,
        created_within: '24 hours',
      },
      created_at: '2025-10-24T11:00:00Z',
      status: 'pending',
    },
    {
      id: 2,
      type: 'unusual_betting',
      severity: 'critical',
      user_email: 'user2@example.com',
      user_id: 'uuid-2',
      description: 'Unusual betting pattern detected - consistent wins on unlikely outcomes',
      details: {
        win_rate: '95%',
        total_bets: 47,
        profit: '$12,450',
      },
      created_at: '2025-10-24T10:30:00Z',
      status: 'pending',
    },
    {
      id: 3,
      type: 'rapid_deposits',
      severity: 'medium',
      user_email: 'user3@example.com',
      user_id: 'uuid-3',
      description: 'Rapid successive deposits from multiple payment methods',
      details: {
        deposits_count: 8,
        total_amount: '$5,000',
        timeframe: '2 hours',
        methods: ['Credit Card', 'PayPal', 'Bank Transfer'],
      },
      created_at: '2025-10-24T09:15:00Z',
      status: 'pending',
    },
  ]);

  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  const handleInvestigate = (alert) => {
    setSelectedAlert(alert);
    setShowDetailsModal(true);
  };

  const handleResolve = async (alertId, resolution) => {
    try {
      // TODO: API call to resolve alert
      setAlerts(alerts.map(a => 
        a.id === alertId ? { ...a, status: resolution } : a
      ));
      toast.success(`Alert marked as ${resolution}`);
      setShowDetailsModal(false);
    } catch (error) {
      toast.error('Failed to update alert');
    }
  };

  const handleDismiss = async (alertId) => {
    try {
      // TODO: API call to dismiss alert
      setAlerts(alerts.filter(a => a.id !== alertId));
      toast.success('Alert dismissed');
    } catch (error) {
      toast.error('Failed to dismiss alert');
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'high':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'low':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'multiple_accounts':
        return <Users className="w-5 h-5" />;
      case 'unusual_betting':
        return <TrendingUp className="w-5 h-5" />;
      case 'rapid_deposits':
        return <DollarSign className="w-5 h-5" />;
      default:
        return <AlertTriangle className="w-5 h-5" />;
    }
  };

  const getTypeLabel = (type) => {
    return type.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const getTimeAgo = (timestamp) => {
    const now = new Date();
    const past = new Date(timestamp);
    const diffMs = now - past;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  };

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center">
              <Shield className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Fraud Alerts</h2>
              <p className="text-sm text-gray-400">
                {alerts.filter(a => a.status === 'pending').length} active alerts
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              alerts.some(a => a.severity === 'critical') 
                ? 'bg-red-500/20 text-red-400' 
                : 'bg-green-500/20 text-green-400'
            }`}>
              {alerts.some(a => a.severity === 'critical') ? 'Action Required' : 'All Clear'}
            </span>
          </div>
        </div>
      </div>

      {/* Alerts List */}
      <div className="divide-y divide-gray-700">
        {alerts.length === 0 ? (
          <div className="p-12 text-center">
            <Shield className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No fraud alerts</p>
            <p className="text-sm text-gray-500 mt-2">System is secure! 🛡️</p>
          </div>
        ) : (
          alerts.map((alert) => (
            <div key={alert.id} className="p-5 hover:bg-gray-700/30 transition-colors">
              <div className="flex items-start justify-between">
                {/* Left Side - Alert Info */}
                <div className="flex-1">
                  <div className="flex items-start space-x-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      alert.severity === 'critical' ? 'bg-red-500/20' :
                      alert.severity === 'high' ? 'bg-orange-500/20' :
                      alert.severity === 'medium' ? 'bg-yellow-500/20' :
                      'bg-blue-500/20'
                    }`}>
                      {getTypeIcon(alert.type)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h3 className="text-sm font-semibold text-white">
                          {getTypeLabel(alert.type)}
                        </h3>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getSeverityColor(alert.severity)}`}>
                          {alert.severity.toUpperCase()}
                        </span>
                        <span className="text-xs text-gray-500">
                          {getTimeAgo(alert.created_at)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300 mb-2">{alert.description}</p>
                      <p className="text-xs text-gray-400">
                        User: <span className="text-gray-300">{alert.user_email}</span>
                      </p>
                      
                      {/* Quick Details */}
                      <div className="mt-3 flex flex-wrap gap-4">
                        {Object.entries(alert.details).slice(0, 3).map(([key, value]) => (
                          <div key={key} className="text-xs">
                            <span className="text-gray-500">{key.replace(/_/g, ' ')}: </span>
                            <span className="text-white font-medium">
                              {Array.isArray(value) ? value.join(', ') : value}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Side - Actions */}
                <div className="flex flex-col space-y-2 ml-6">
                  <button
                    onClick={() => handleInvestigate(alert)}
                    className="flex items-center space-x-2 px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 font-medium rounded-lg transition-colors text-sm border border-blue-500/30"
                  >
                    <Eye className="w-4 h-4" />
                    <span>Investigate</span>
                  </button>
                  <button
                    onClick={() => handleDismiss(alert.id)}
                    className="flex items-center space-x-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 font-medium rounded-lg transition-colors text-sm"
                  >
                    <X className="w-4 h-4" />
                    <span>Dismiss</span>
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Investigation Modal */}
      {showDetailsModal && selectedAlert && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={() => setShowDetailsModal(false)}
          />

          {/* Modal */}
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative bg-gray-800 rounded-xl shadow-2xl border border-gray-700 w-full max-w-2xl">
              {/* Header */}
              <div className="flex items-center justify-between p-5 border-b border-gray-700">
                <div className="flex items-center space-x-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    selectedAlert.severity === 'critical' ? 'bg-red-500/20' :
                    selectedAlert.severity === 'high' ? 'bg-orange-500/20' :
                    'bg-yellow-500/20'
                  }`}>
                    {getTypeIcon(selectedAlert.type)}
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">
                      {getTypeLabel(selectedAlert.type)}
                    </h3>
                    <p className="text-sm text-gray-400">{selectedAlert.user_email}</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowDetailsModal(false)}
                  className="p-1 hover:bg-gray-700 rounded transition-colors"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>

              {/* Content */}
              <div className="p-5">
                <div className="space-y-4">
                  <div>
                    <h4 className="text-sm font-semibold text-white mb-2">Description</h4>
                    <p className="text-sm text-gray-300">{selectedAlert.description}</p>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-white mb-2">Details</h4>
                    <div className="bg-gray-900 rounded-lg p-4 space-y-2">
                      {Object.entries(selectedAlert.details).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-sm text-gray-400">
                            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                          </span>
                          <span className="text-sm text-white font-medium">
                            {Array.isArray(value) ? value.join(', ') : value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-white mb-2">Severity Level</h4>
                    <span className={`inline-flex px-3 py-1 rounded-full text-sm font-medium border ${getSeverityColor(selectedAlert.severity)}`}>
                      {selectedAlert.severity.toUpperCase()}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-white mb-2">Detected</h4>
                    <p className="text-sm text-gray-300">
                      {new Date(selectedAlert.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-end space-x-3 p-5 border-t border-gray-700">
                <button
                  onClick={() => handleResolve(selectedAlert.id, 'false_positive')}
                  className="px-4 py-2 text-sm text-gray-400 hover:bg-gray-700 rounded-lg transition-colors"
                >
                  Mark as False Positive
                </button>
                <button
                  onClick={() => handleResolve(selectedAlert.id, 'resolved')}
                  className="flex items-center space-x-2 px-4 py-2 text-sm bg-green-400 hover:bg-green-500 text-gray-900 font-medium rounded-lg transition-colors"
                >
                  <CheckCircle className="w-4 h-4" />
                  <span>Resolve Alert</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FraudAlerts;
