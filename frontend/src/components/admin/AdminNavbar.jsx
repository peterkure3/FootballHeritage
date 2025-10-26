import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, 
  Bell, 
  User, 
  LogOut, 
  ArrowLeft, 
  Menu,
  Shield,
  Settings
} from 'lucide-react';
import useAuthStore from '../../stores/authStore';

/**
 * Admin Top Navbar
 * Top navigation bar for admin panel
 */

const AdminNavbar = ({ onMenuToggle }) => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleBackToUserView = () => {
    navigate('/dashboard');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="sticky top-0 z-30 h-16 bg-slate-800 border-b border-slate-700 px-4 lg:px-6">
      <div className="h-full flex items-center justify-between">
        {/* Left Section */}
        <div className="flex items-center space-x-4">
          {/* Mobile Menu Toggle */}
          <button
            onClick={onMenuToggle}
            className="lg:hidden p-2 hover:bg-slate-700 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <Menu className="w-6 h-6" />
          </button>

          {/* Admin Branding */}
          <div className="flex items-center space-x-2">
            <Shield className="w-6 h-6 text-green-500" />
            <span className="hidden sm:block text-white font-semibold text-lg">Admin Panel</span>
          </div>
        </div>

        {/* Center Section - Search */}
        <div className="hidden md:flex flex-1 max-w-md mx-8">
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search events, users, bets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500"
            />
          </div>
        </div>

        {/* Right Section */}
        <div className="flex items-center space-x-2 lg:space-x-4">
          {/* Back to User View */}
          <button
            onClick={handleBackToUserView}
            className="hidden sm:flex items-center space-x-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm font-medium">User View</span>
          </button>

          {/* Notifications */}
          <button className="relative p-2 hover:bg-slate-700 rounded-lg transition-colors text-gray-400 hover:text-white">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>

          {/* Profile Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className="flex items-center space-x-2 p-2 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="hidden lg:block text-left">
                <p className="text-sm font-medium text-white">{user?.username || 'Admin'}</p>
                <p className="text-xs text-gray-400">Administrator</p>
              </div>
            </button>

            {/* Dropdown Menu */}
            {showProfileMenu && (
              <>
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={() => setShowProfileMenu(false)}
                />
                <div className="absolute right-0 mt-2 w-56 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50">
                  <div className="p-3 border-b border-slate-700">
                    <p className="text-sm font-medium text-white">{user?.username || 'Admin'}</p>
                    <p className="text-xs text-gray-400">{user?.email || 'admin@footballheritage.com'}</p>
                  </div>
                  <div className="py-2">
                    <button
                      onClick={() => {
                        setShowProfileMenu(false);
                        navigate('/admin/settings');
                      }}
                      className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-300 hover:bg-slate-700 transition-colors"
                    >
                      <Settings className="w-4 h-4" />
                      <span>Settings</span>
                    </button>
                    <button
                      onClick={() => {
                        setShowProfileMenu(false);
                        handleBackToUserView();
                      }}
                      className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-300 hover:bg-slate-700 transition-colors sm:hidden"
                    >
                      <ArrowLeft className="w-4 h-4" />
                      <span>Back to User View</span>
                    </button>
                  </div>
                  <div className="border-t border-slate-700 py-2">
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-red-400 hover:bg-slate-700 transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>Logout</span>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default AdminNavbar;
