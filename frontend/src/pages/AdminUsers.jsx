import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import { 
  Search, 
  Filter, 
  MoreVertical, 
  CheckCircle, 
  XCircle,
  Mail,
  Calendar,
  DollarSign,
  Shield,
  Ban,
  UserCheck
} from 'lucide-react';

/**
 * Admin Users Management Page
 * View and manage all platform users
 */

const AdminUsers = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [users, setUsers] = useState([
    { id: 1, username: 'john_doe', email: 'john@example.com', balance: 1250.50, is_verified: true, is_admin: false, created_at: '2025-10-20', status: 'active' },
    { id: 2, username: 'jane_smith', email: 'jane@example.com', balance: 500.00, is_verified: false, is_admin: false, created_at: '2025-10-22', status: 'active' },
    { id: 3, username: 'mike_wilson', email: 'mike@example.com', balance: 3200.75, is_verified: true, is_admin: false, created_at: '2025-10-18', status: 'active' },
    { id: 4, username: 'sarah_jones', email: 'sarah@example.com', balance: 890.25, is_verified: true, is_admin: true, created_at: '2025-10-15', status: 'active' },
    { id: 5, username: 'bob_brown', email: 'bob@example.com', balance: 150.00, is_verified: false, is_admin: false, created_at: '2025-10-25', status: 'suspended' },
  ]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user?.is_admin && !user?.is_super_admin) {
      toast.error('Access denied. Admin privileges required.');
      navigate('/');
      return;
    }
    // TODO: Fetch real users from API
  }, [user, navigate]);

  const filteredUsers = users.filter(u => {
    const matchesSearch = u.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         u.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || u.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleVerifyUser = (userId) => {
    setUsers(users.map(u => u.id === userId ? { ...u, is_verified: true } : u));
    toast.success('User verified successfully');
  };

  const handleSuspendUser = (userId) => {
    setUsers(users.map(u => u.id === userId ? { ...u, status: 'suspended' } : u));
    toast.success('User suspended');
  };

  const handleActivateUser = (userId) => {
    setUsers(users.map(u => u.id === userId ? { ...u, status: 'active' } : u));
    toast.success('User activated');
  };

  return (
    <div>
      <div className="max-w-[1800px] mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">User Management</h1>
          <p className="text-gray-400 mt-1 text-sm">
            View and manage all platform users
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Total Users</span>
              <Shield className="w-5 h-5 text-blue-400" />
            </div>
            <p className="text-2xl font-bold text-white">{users.length}</p>
          </div>
          
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Verified</span>
              <CheckCircle className="w-5 h-5 text-green-400" />
            </div>
            <p className="text-2xl font-bold text-white">{users.filter(u => u.is_verified).length}</p>
          </div>
          
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Suspended</span>
              <Ban className="w-5 h-5 text-red-400" />
            </div>
            <p className="text-2xl font-bold text-white">{users.filter(u => u.status === 'suspended').length}</p>
          </div>
          
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Admins</span>
              <Shield className="w-5 h-5 text-purple-400" />
            </div>
            <p className="text-2xl font-bold text-white">{users.filter(u => u.is_admin).length}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by username or email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
              />
            </div>
            
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-green-500"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
            </select>
          </div>
        </div>

        {/* Users Table */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700 bg-gray-900">
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Balance
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Joined
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {filteredUsers.map((userItem) => (
                  <tr key={userItem.id} className="hover:bg-gray-700/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center mr-3">
                          <span className="text-sm font-medium text-gray-300">
                            {userItem.username.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-white">{userItem.username}</p>
                          <p className="text-xs text-gray-400">{userItem.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm font-medium text-white">${userItem.balance.toFixed(2)}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          userItem.status === 'active' 
                            ? 'bg-green-400/10 text-green-400' 
                            : 'bg-red-400/10 text-red-400'
                        }`}>
                          {userItem.status}
                        </span>
                        {userItem.is_verified && (
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        )}
                        {userItem.is_admin && (
                          <Shield className="w-4 h-4 text-purple-400" />
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-400">
                        {new Date(userItem.created_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        {!userItem.is_verified && (
                          <button
                            onClick={() => handleVerifyUser(userItem.id)}
                            className="p-2 hover:bg-gray-600 rounded-lg transition-colors"
                            title="Verify User"
                          >
                            <UserCheck className="w-4 h-4 text-green-400" />
                          </button>
                        )}
                        {userItem.status === 'active' ? (
                          <button
                            onClick={() => handleSuspendUser(userItem.id)}
                            className="p-2 hover:bg-gray-600 rounded-lg transition-colors"
                            title="Suspend User"
                          >
                            <Ban className="w-4 h-4 text-red-400" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleActivateUser(userItem.id)}
                            className="p-2 hover:bg-gray-600 rounded-lg transition-colors"
                            title="Activate User"
                          >
                            <CheckCircle className="w-4 h-4 text-green-400" />
                          </button>
                        )}
                        <button className="p-2 hover:bg-gray-600 rounded-lg transition-colors">
                          <MoreVertical className="w-4 h-4 text-gray-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminUsers;
