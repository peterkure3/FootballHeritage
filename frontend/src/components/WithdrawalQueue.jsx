import { useState } from 'react';
import { DollarSign, CheckCircle, X, AlertCircle, Clock, User, CreditCard } from 'lucide-react';
import { toast } from 'react-hot-toast';

/**
 * Withdrawal Approval Queue Component
 * Displays pending withdrawal requests with approve/reject controls
 */

const WithdrawalQueue = () => {
  const [withdrawals, setWithdrawals] = useState([
    {
      id: 1,
      user_email: 'user1@example.com',
      user_id: 'uuid-1',
      amount: 500.00,
      method: 'Bank Transfer',
      account_details: '**** **** **** 1234',
      requested_at: '2025-10-24T10:30:00Z',
      status: 'pending',
      risk_score: 'low',
    },
    {
      id: 2,
      user_email: 'user2@example.com',
      user_id: 'uuid-2',
      amount: 1250.50,
      method: 'PayPal',
      account_details: 'user2@paypal.com',
      requested_at: '2025-10-24T09:15:00Z',
      status: 'pending',
      risk_score: 'medium',
    },
    {
      id: 3,
      user_email: 'user3@example.com',
      user_id: 'uuid-3',
      amount: 3500.00,
      method: 'Cryptocurrency',
      account_details: '0x742d...3f8a',
      requested_at: '2025-10-24T08:00:00Z',
      status: 'pending',
      risk_score: 'high',
    },
  ]);

  const [selectedWithdrawal, setSelectedWithdrawal] = useState(null);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const handleApprove = async (withdrawal) => {
    try {
      // TODO: API call to approve withdrawal
      setWithdrawals(withdrawals.filter(w => w.id !== withdrawal.id));
      toast.success(`Withdrawal of $${withdrawal.amount} approved`);
    } catch (error) {
      toast.error('Failed to approve withdrawal');
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      toast.error('Please provide a reason for rejection');
      return;
    }

    try {
      // TODO: API call to reject withdrawal
      setWithdrawals(withdrawals.filter(w => w.id !== selectedWithdrawal.id));
      toast.success('Withdrawal rejected');
      setShowRejectModal(false);
      setRejectReason('');
      setSelectedWithdrawal(null);
    } catch (error) {
      toast.error('Failed to reject withdrawal');
    }
  };

  const openRejectModal = (withdrawal) => {
    setSelectedWithdrawal(withdrawal);
    setShowRejectModal(true);
  };

  const getRiskColor = (risk) => {
    switch (risk) {
      case 'low':
        return 'bg-green-400/10 text-green-400 border-green-400/20';
      case 'medium':
        return 'bg-yellow-400/10 text-yellow-400 border-yellow-400/20';
      case 'high':
        return 'bg-red-400/10 text-red-400 border-red-400/20';
      default:
        return 'bg-gray-400/10 text-gray-400 border-gray-400/20';
    }
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
            <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Withdrawal Queue</h2>
              <p className="text-sm text-gray-400">{withdrawals.length} pending requests</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-400">
              Total: <span className="font-semibold text-white">
                ${withdrawals.reduce((sum, w) => sum + w.amount, 0).toFixed(2)}
              </span>
            </span>
          </div>
        </div>
      </div>

      {/* Withdrawals List */}
      <div className="divide-y divide-gray-700">
        {withdrawals.length === 0 ? (
          <div className="p-12 text-center">
            <CheckCircle className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No pending withdrawals</p>
            <p className="text-sm text-gray-500 mt-2">All caught up! 🎉</p>
          </div>
        ) : (
          withdrawals.map((withdrawal) => (
            <div key={withdrawal.id} className="p-5 hover:bg-gray-700/30 transition-colors">
              <div className="flex items-start justify-between">
                {/* Left Side - User & Details */}
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
                      <User className="w-5 h-5 text-gray-400" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{withdrawal.user_email}</p>
                      <div className="flex items-center space-x-2 mt-1">
                        <Clock className="w-3 h-3 text-gray-500" />
                        <span className="text-xs text-gray-500">
                          {getTimeAgo(withdrawal.requested_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 ml-13">
                    <div>
                      <p className="text-xs text-gray-400 mb-1">Amount</p>
                      <p className="text-lg font-bold text-white">${withdrawal.amount.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 mb-1">Method</p>
                      <div className="flex items-center space-x-2">
                        <CreditCard className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-white">{withdrawal.method}</span>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 mb-1">Account</p>
                      <p className="text-sm text-gray-300">{withdrawal.account_details}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 mb-1">Risk Level</p>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getRiskColor(withdrawal.risk_score)}`}>
                        {withdrawal.risk_score.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Right Side - Actions */}
                <div className="flex flex-col space-y-2 ml-6">
                  <button
                    onClick={() => handleApprove(withdrawal)}
                    className="flex items-center space-x-2 px-4 py-2 bg-green-400 hover:bg-green-500 text-gray-900 font-medium rounded-lg transition-colors text-sm"
                  >
                    <CheckCircle className="w-4 h-4" />
                    <span>Approve</span>
                  </button>
                  <button
                    onClick={() => openRejectModal(withdrawal)}
                    className="flex items-center space-x-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 font-medium rounded-lg transition-colors text-sm border border-red-500/30"
                  >
                    <X className="w-4 h-4" />
                    <span>Reject</span>
                  </button>
                </div>
              </div>

              {/* Risk Warning */}
              {withdrawal.risk_score === 'high' && (
                <div className="mt-4 ml-13 flex items-start space-x-2 p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                  <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-400">High Risk Transaction</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Review user history and verify identity before approval
                    </p>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={() => setShowRejectModal(false)}
          />

          {/* Modal */}
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative bg-gray-800 rounded-xl shadow-2xl border border-gray-700 w-full max-w-md">
              {/* Header */}
              <div className="flex items-center justify-between p-5 border-b border-gray-700">
                <h3 className="text-lg font-semibold text-white">Reject Withdrawal</h3>
                <button
                  onClick={() => setShowRejectModal(false)}
                  className="p-1 hover:bg-gray-700 rounded transition-colors"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>

              {/* Content */}
              <div className="p-5">
                <div className="mb-4">
                  <p className="text-sm text-gray-400 mb-2">
                    You are rejecting a withdrawal of{' '}
                    <span className="font-semibold text-white">
                      ${selectedWithdrawal?.amount.toFixed(2)}
                    </span>{' '}
                    for{' '}
                    <span className="font-semibold text-white">
                      {selectedWithdrawal?.user_email}
                    </span>
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Reason for Rejection *
                  </label>
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Provide a detailed reason for rejecting this withdrawal..."
                    rows={4}
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-400 text-sm resize-none"
                  />
                </div>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-end space-x-3 p-5 border-t border-gray-700">
                <button
                  onClick={() => setShowRejectModal(false)}
                  className="px-4 py-2 text-sm text-gray-400 hover:bg-gray-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleReject}
                  className="px-4 py-2 text-sm bg-red-500 hover:bg-red-600 text-white font-medium rounded-lg transition-colors"
                >
                  Reject Withdrawal
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WithdrawalQueue;
