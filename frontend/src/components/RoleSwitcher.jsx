import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, User } from 'lucide-react';
import useAuthStore from '../stores/authStore';

/**
 * Role Switcher Component
 * 
 * Allows admins to switch between user and admin views
 * Features:
 * - Dropdown menu for role selection
 * - Visual indicator of current role
 * - Only visible to admin users
 */

const RoleSwitcher = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [currentRole, setCurrentRole] = useState('user'); // 'user' or 'admin'

  // Update current role based on current route
  useEffect(() => {
    if (location.pathname.startsWith('/admin')) {
      setCurrentRole('admin');
    } else {
      setCurrentRole('user');
    }
  }, [location.pathname]);

  // Don't show if not admin
  if (!user?.is_admin && !user?.is_super_admin) {
    return null;
  }

  const handleRoleSwitch = (role) => {
    setCurrentRole(role);
    setIsOpen(false);
    
    if (role === 'admin') {
      navigate('/admin');
    } else {
      navigate('/dashboard');
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors border border-gray-700"
        title={currentRole === 'admin' ? 'Admin View - Click to switch' : 'User View - Click to switch'}
      >
        {currentRole === 'admin' ? (
          <Shield className="w-5 h-5 text-green-400" />
        ) : (
          <User className="w-5 h-5 text-gray-300" />
        )}
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown Menu */}
          <div className="absolute right-0 mt-2 w-56 rounded-lg shadow-2xl bg-gray-800 border border-gray-700 z-20">
            <div className="py-1">
              {/* User View Option */}
              <button
                onClick={() => handleRoleSwitch('user')}
                className={`
                  w-full flex items-center px-4 py-3 text-sm hover:bg-gray-700 transition-colors
                  ${currentRole === 'user' ? 'bg-gray-700/50' : ''}
                `}
              >
                <User className={`w-5 h-5 mr-3 ${currentRole === 'user' ? 'text-gray-300' : 'text-gray-500'}`} />
                <div className="flex-1 text-left">
                  <p className={`font-medium ${currentRole === 'user' ? 'text-white' : 'text-gray-300'}`}>
                    User View
                  </p>
                  <p className="text-xs text-gray-500">Browse and place bets</p>
                </div>
                {currentRole === 'user' && (
                  <div className="w-2 h-2 rounded-full bg-gray-400" />
                )}
              </button>

              {/* Divider */}
              <div className="border-t border-gray-700 my-1" />

              {/* Admin View Option */}
              <button
                onClick={() => handleRoleSwitch('admin')}
                className={`
                  w-full flex items-center px-4 py-3 text-sm hover:bg-gray-700 transition-colors
                  ${currentRole === 'admin' ? 'bg-green-500/10' : ''}
                `}
              >
                <Shield className={`w-5 h-5 mr-3 ${currentRole === 'admin' ? 'text-green-400' : 'text-gray-500'}`} />
                <div className="flex-1 text-left">
                  <p className={`font-medium ${currentRole === 'admin' ? 'text-green-400' : 'text-gray-300'}`}>
                    Admin View
                  </p>
                  <p className="text-xs text-gray-500">Manage platform</p>
                </div>
                {currentRole === 'admin' && (
                  <div className="w-2 h-2 rounded-full bg-green-400" />
                )}
              </button>

              {/* Super Admin Badge (if applicable) */}
              {user?.is_super_admin && (
                <>
                  <div className="border-t border-gray-700 my-1" />
                  <div className="px-4 py-2 bg-purple-500/10">
                    <div className="flex items-center space-x-2">
                      <Shield className="w-4 h-4 text-purple-400" />
                      <span className="text-xs font-medium text-purple-400">Super Admin</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Full system access</p>
                  </div>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default RoleSwitcher;
