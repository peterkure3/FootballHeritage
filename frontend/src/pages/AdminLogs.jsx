import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import { FileText, User, Shield, AlertTriangle, CheckCircle } from 'lucide-react';

const AdminLogs = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  useEffect(() => {
    if (!user?.is_admin && !user?.is_super_admin) {
      toast.error('Access denied');
      navigate('/');
    }
  }, [user, navigate]);

  const logs = [
    { id: 1, action: 'User Login', user: 'john_doe', type: 'auth', timestamp: '2025-10-26 14:32:15', status: 'success' },
    { id: 2, action: 'Bet Placed', user: 'jane_smith', type: 'bet', timestamp: '2025-10-26 14:28:42', status: 'success' },
    { id: 3, action: 'Withdrawal Request', user: 'mike_wilson', type: 'transaction', timestamp: '2025-10-26 14:15:23', status: 'pending' },
    { id: 4, action: 'Failed Login Attempt', user: 'unknown', type: 'security', timestamp: '2025-10-26 14:05:11', status: 'failed' },
    { id: 5, action: 'User Verified', user: 'sarah_jones', type: 'admin', timestamp: '2025-10-26 13:58:33', status: 'success' },
  ];

  const getIcon = (type) => {
    switch(type) {
      case 'auth': return <User className="w-5 h-5 text-blue-400" />;
      case 'admin': return <Shield className="w-5 h-5 text-purple-400" />;
      case 'security': return <AlertTriangle className="w-5 h-5 text-red-400" />;
      default: return <FileText className="w-5 h-5 text-gray-400" />;
    }
  };

  return (
    <div>
      <div className="max-w-[1800px] mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">Audit Logs</h1>
          <p className="text-gray-400 mt-1 text-sm">System activity and security logs</p>
        </div>

        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700 bg-gray-900">
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase">Type</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase">Action</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase">User</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase">Timestamp</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-700/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        {getIcon(log.type)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-white">{log.action}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-300">{log.user}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-400">{log.timestamp}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        log.status === 'success' ? 'bg-green-400/10 text-green-400' :
                        log.status === 'failed' ? 'bg-red-400/10 text-red-400' :
                        'bg-yellow-400/10 text-yellow-400'
                      }`}>
                        {log.status}
                      </span>
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

export default AdminLogs;
