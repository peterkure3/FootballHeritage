import { useState } from 'react';
import { X, Mail, Calendar, DollarSign, Shield, Ban, CheckCircle, Activity, CreditCard } from 'lucide-react';
import { toast } from 'react-hot-toast';

/**
 * User Details Modal Component
 * Displays comprehensive user information and management controls
 */

const UserDetailsModal = ({ user, isOpen, onClose, onUpdate }) => {
  const [activeTab, setActiveTab] = useState('overview'); // overview, transactions, bets, activity
  const [isEditing, setIsEditing] = useState(false);
  const [editedUser, setEditedUser] = useState(user);

  if (!isOpen || !user) return null;

  const handleSave = async () => {
    try {
      // TODO: API call to update user
      onUpdate(editedUser);
      setIsEditing(false);
      toast.success('User updated successfully');
    } catch {
      toast.error('Failed to update user');
    }
  };

  const handleVerify = async () => {
    try {
      // TODO: API call to verify user
      toast.success('User verified successfully');
      onUpdate({ ...user, is_verified: true });
    } catch {
      toast.error('Failed to verify user');
    }
  };

  const handleBan = async () => {
    try {
      // TODO: API call to ban user
      toast.success('User banned successfully');
      onUpdate({ ...user, is_active: false });
    } catch {
      toast.error('Failed to ban user');
    }
  };

  const handleUnban = async () => {
    try {
      // TODO: API call to unban user
      toast.success('User unbanned successfully');
      onUpdate({ ...user, is_active: true });
    } catch {
      toast.error('Failed to unban user');
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-card rounded-xl shadow-2xl border border-card-border w-full max-w-4xl">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-card-border">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 rounded-full bg-card-hover flex items-center justify-center">
                <span className="text-lg font-bold text-heritage-ink">
                  {user.email.charAt(0).toUpperCase()}
                </span>
              </div>
              <div>
                <h2 className="text-xl font-bold text-heritage-ink">{user.email}</h2>
                <div className="flex items-center space-x-2 mt-1">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    user.is_verified 
                      ? 'bg-green-400/10 text-green-700'
                      : 'bg-yellow-400/10 text-yellow-700'
                  }`}>
                    {user.is_verified ? 'Verified' : 'Unverified'}
                  </span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    user.is_active 
                      ? 'bg-blue-400/10 text-blue-700'
                      : 'bg-red-400/10 text-red-700'
                  }`}>
                    {user.is_active ? 'Active' : 'Banned'}
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close user details modal"
              className="p-2 hover:bg-card-hover rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-heritage-muted" />
            </button>
          </div>

          {/* Tabs */}
          <div className="border-b border-card-border">
            <nav className="flex space-x-8 px-6">
              {[
                { id: 'overview', label: 'Overview' },
                { id: 'transactions', label: 'Transactions' },
                { id: 'bets', label: 'Betting History' },
                { id: 'activity', label: 'Activity Log' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-green-400 text-green-700'
                      : 'border-transparent text-heritage-muted hover:text-heritage-ink'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="p-6 max-h-[600px] overflow-y-auto">
            {activeTab === 'overview' && (
              <div className="space-y-6">
                {/* Quick Stats */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-card rounded-lg p-4 border border-card-border">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                        <DollarSign className="w-5 h-5 text-green-700" />
                      </div>
                      <div>
                        <p className="text-xs text-heritage-muted">Balance</p>
                        <p className="text-lg font-bold text-heritage-ink">${user.balance?.toFixed(2) || '0.00'}</p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-card rounded-lg p-4 border border-card-border">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                        <Activity className="w-5 h-5 text-blue-700" />
                      </div>
                      <div>
                        <p className="text-xs text-heritage-muted">Total Bets</p>
                        <p className="text-lg font-bold text-heritage-ink">{user.total_bets || 0}</p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-card rounded-lg p-4 border border-card-border">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                        <CreditCard className="w-5 h-5 text-purple-700" />
                      </div>
                      <div>
                        <p className="text-xs text-heritage-muted">Total Wagered</p>
                        <p className="text-lg font-bold text-heritage-ink">${user.total_wagered?.toFixed(2) || '0.00'}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* User Information */}
                <div className="bg-card rounded-lg p-5 border border-card-border">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-semibold text-heritage-ink">User Information</h3>
                    {!isEditing ? (
                      <button
                        onClick={() => setIsEditing(true)}
                        className="px-3 py-1 text-sm text-green-700 hover:bg-green-400/10 rounded-lg transition-colors"
                      >
                        Edit
                      </button>
                    ) : (
                      <div className="flex space-x-2">
                        <button
                          onClick={() => setIsEditing(false)}
                          className="px-3 py-1 text-sm text-heritage-muted hover:bg-card-hover rounded-lg transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleSave}
                          className="px-3 py-1 text-sm bg-green-400 text-gray-900 font-medium rounded-lg hover:bg-green-500 transition-colors"
                        >
                          Save
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-heritage-muted mb-1">Email</label>
                      {isEditing ? (
                        <input
                          type="email"
                          value={editedUser.email}
                          onChange={(e) => setEditedUser({ ...editedUser, email: e.target.value })}
                          className="w-full px-3 py-2 bg-card border border-card-border rounded-lg text-heritage-ink text-sm focus:outline-none focus:border-green-400"
                        />
                      ) : (
                        <p className="text-sm text-heritage-ink">{user.email}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs text-heritage-muted mb-1">Joined Date</label>
                      <p className="text-sm text-heritage-ink">
                        {new Date(user.created_at).toLocaleDateString('en-US', { 
                          year: 'numeric', 
                          month: 'long', 
                          day: 'numeric' 
                        })}
                      </p>
                    </div>

                    <div>
                      <label className="block text-xs text-heritage-muted mb-1">First Name</label>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editedUser.first_name || ''}
                          onChange={(e) => setEditedUser({ ...editedUser, first_name: e.target.value })}
                          className="w-full px-3 py-2 bg-card border border-card-border rounded-lg text-heritage-ink text-sm focus:outline-none focus:border-green-400"
                        />
                      ) : (
                        <p className="text-sm text-heritage-ink">{user.first_name || 'N/A'}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs text-heritage-muted mb-1">Last Name</label>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editedUser.last_name || ''}
                          onChange={(e) => setEditedUser({ ...editedUser, last_name: e.target.value })}
                          className="w-full px-3 py-2 bg-card border border-card-border rounded-lg text-heritage-ink text-sm focus:outline-none focus:border-green-400"
                        />
                      ) : (
                        <p className="text-sm text-heritage-ink">{user.last_name || 'N/A'}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs text-heritage-muted mb-1">Phone</label>
                      {isEditing ? (
                        <input
                          type="tel"
                          value={editedUser.phone || ''}
                          onChange={(e) => setEditedUser({ ...editedUser, phone: e.target.value })}
                          className="w-full px-3 py-2 bg-card border border-card-border rounded-lg text-heritage-ink text-sm focus:outline-none focus:border-green-400"
                        />
                      ) : (
                        <p className="text-sm text-heritage-ink">{user.phone || 'N/A'}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs text-heritage-muted mb-1">Last Login</label>
                      <p className="text-sm text-heritage-ink">
                        {user.last_login 
                          ? new Date(user.last_login).toLocaleString() 
                          : 'Never'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Admin Actions */}
                <div className="bg-card rounded-lg p-5 border border-card-border">
                  <h3 className="text-sm font-semibold text-heritage-ink mb-4">Admin Actions</h3>
                  <div className="flex flex-wrap gap-3">
                    {!user.is_verified && (
                      <button
                        onClick={handleVerify}
                        className="flex items-center space-x-2 px-4 py-2 bg-green-400 hover:bg-green-500 text-gray-900 font-medium rounded-lg transition-colors text-sm"
                      >
                        <CheckCircle className="w-4 h-4" />
                        <span>Verify User</span>
                      </button>
                    )}
                    
                    {user.is_active ? (
                      <button
                        onClick={handleBan}
                        className="flex items-center space-x-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-700 font-medium rounded-lg transition-colors text-sm border border-red-500/30"
                      >
                        <Ban className="w-4 h-4" />
                        <span>Ban User</span>
                      </button>
                    ) : (
                      <button
                        onClick={handleUnban}
                        className="flex items-center space-x-2 px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-700 font-medium rounded-lg transition-colors text-sm border border-blue-500/30"
                      >
                        <Shield className="w-4 h-4" />
                        <span>Unban User</span>
                      </button>
                    )}

                    <button className="flex items-center space-x-2 px-4 py-2 bg-card-hover hover:bg-card-hover text-heritage-ink font-medium rounded-lg transition-colors text-sm">
                      <Mail className="w-4 h-4" />
                      <span>Send Email</span>
                    </button>

                    <button className="flex items-center space-x-2 px-4 py-2 bg-card-hover hover:bg-card-hover text-heritage-ink font-medium rounded-lg transition-colors text-sm">
                      <Calendar className="w-4 h-4" />
                      <span>View Calendar</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'transactions' && (
              <div className="text-center py-12">
                <CreditCard className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-heritage-muted">Transaction history will be displayed here</p>
                <p className="text-sm text-heritage-muted mt-2">Coming soon...</p>
              </div>
            )}

            {activeTab === 'bets' && (
              <div className="text-center py-12">
                <Activity className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-heritage-muted">Betting history will be displayed here</p>
                <p className="text-sm text-heritage-muted mt-2">Coming soon...</p>
              </div>
            )}

            {activeTab === 'activity' && (
              <div className="text-center py-12">
                <Shield className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-heritage-muted">Activity log will be displayed here</p>
                <p className="text-sm text-heritage-muted mt-2">Coming soon...</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserDetailsModal;
