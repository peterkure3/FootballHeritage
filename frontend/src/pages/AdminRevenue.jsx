import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import { DollarSign, TrendingUp, Download, Calendar } from 'lucide-react';

const AdminRevenue = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  useEffect(() => {
    if (!user?.is_admin && !user?.is_super_admin) {
      toast.error('Access denied');
      navigate('/');
    }
  }, [user, navigate]);

  return (
    <div>
      <div className="max-w-[1800px] mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">Revenue Management</h1>
          <p className="text-gray-400 mt-1 text-sm">Financial overview and reports</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <DollarSign className="w-8 h-8 text-green-400" />
              <TrendingUp className="w-5 h-5 text-green-400" />
            </div>
            <p className="text-3xl font-bold text-white mb-2">$45,678.90</p>
            <p className="text-sm text-gray-400">Total Revenue</p>
          </div>

          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <Calendar className="w-8 h-8 text-blue-400" />
              <span className="text-xs text-green-400">+26%</span>
            </div>
            <p className="text-3xl font-bold text-white mb-2">$8,234.50</p>
            <p className="text-sm text-gray-400">This Week</p>
          </div>

          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <DollarSign className="w-8 h-8 text-purple-400" />
              <span className="text-xs text-green-400">+18%</span>
            </div>
            <p className="text-3xl font-bold text-white mb-2">$51.20</p>
            <p className="text-sm text-gray-400">Avg Bet Size</p>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white">Revenue Breakdown</h2>
            <button className="flex items-center space-x-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors">
              <Download className="w-4 h-4" />
              <span>Export Report</span>
            </button>
          </div>
          
          <div className="text-center py-12 text-gray-400">
            <DollarSign className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p>Revenue analytics and detailed reports coming soon</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminRevenue;
