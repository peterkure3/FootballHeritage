import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import Navbar from '../components/Navbar';
import BetManagement from '../components/BetManagement';

/**
 * Admin Bets Page
 * Full page for bet management
 */

const AdminBets = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  useEffect(() => {
    // Check if user is admin
    if (!user?.is_admin && !user?.is_super_admin) {
      toast.error('Access denied. Admin privileges required.');
      navigate('/');
      return;
    }
  }, [user, navigate]);

  return (
    <div className="min-h-screen bg-gray-900">
      <Navbar />
      
      <div className="max-w-[1800px] mx-auto px-6 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">Bet Management</h1>
          <p className="text-gray-400 mt-1 text-sm">
            View and manage all platform bets
          </p>
        </div>

        {/* Bet Management Component */}
        <BetManagement />
      </div>
    </div>
  );
};

export default AdminBets;
