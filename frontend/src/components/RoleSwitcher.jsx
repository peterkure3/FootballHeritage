import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, User, ChevronDown } from 'lucide-react';
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
  const { user } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [currentRole, setCurrentRole] = useState('user'); // 'user' or 'admin'

  // Debug logging
  console.log('RoleSwitcher - User:', user);
  console.log('RoleSwitcher - is_admin:', user?.is_admin);
  console.log('RoleSwitcher - is_super_admin:', user?.is_super_admin);

  // Don't show if not admin
  if (!user?.is_admin && !user?.is_super_admin) {
    console.log('RoleSwitcher - Not showing (user is not admin)');
    return null;
  }

  console.log('RoleSwitcher - Showing!');

  const handleRoleSwitch = (role) => {
    setCurrentRole(role);
    setIsOpen(false);
    
    if (role === 'admin') {
      navigate('/admin');
    } else {
      navigate('/');
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors"
      >
        {currentRole === 'admin' ? (
          <Shield className="w-5 h-5 text-green-600" />
        ) : (
          <User className="w-5 h-5 text-blue-600" />
        )}
        <span className="text-sm font-medium text-gray-700">
          {currentRole === 'admin' ? 'Admin View' : 'User View'}
        </span>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown Menu */}
          <div className="absolute right-0 mt-2 w-56 rounded-lg shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-20">
            <div className="py-1">
              {/* User View Option */}
              <button
                onClick={() => handleRoleSwitch('user')}
                className={`
                  w-full flex items-center px-4 py-3 text-sm hover:bg-gray-50 transition-colors
                  ${currentRole === 'user' ? 'bg-blue-50' : ''}
                `}
              >
                <User className={`w-5 h-5 mr-3 ${currentRole === 'user' ? 'text-blue-600' : 'text-gray-400'}`} />
                <div className="flex-1 text-left">
                  <p className={`font-medium ${currentRole === 'user' ? 'text-blue-600' : 'text-gray-900'}`}>
                    User View
                  </p>
                  <p className="text-xs text-gray-500">Browse and place bets</p>
                </div>
                {currentRole === 'user' && (
                  <div className="w-2 h-2 rounded-full bg-blue-600" />
                )}
              </button>

              {/* Divider */}
              <div className="border-t border-gray-100 my-1" />

              {/* Admin View Option */}
              <button
                onClick={() => handleRoleSwitch('admin')}
                className={`
                  w-full flex items-center px-4 py-3 text-sm hover:bg-gray-50 transition-colors
                  ${currentRole === 'admin' ? 'bg-green-50' : ''}
                `}
              >
                <Shield className={`w-5 h-5 mr-3 ${currentRole === 'admin' ? 'text-green-600' : 'text-gray-400'}`} />
                <div className="flex-1 text-left">
                  <p className={`font-medium ${currentRole === 'admin' ? 'text-green-600' : 'text-gray-900'}`}>
                    Admin View
                  </p>
                  <p className="text-xs text-gray-500">Manage platform</p>
                </div>
                {currentRole === 'admin' && (
                  <div className="w-2 h-2 rounded-full bg-green-600" />
                )}
              </button>

              {/* Super Admin Badge (if applicable) */}
              {user?.is_super_admin && (
                <>
                  <div className="border-t border-gray-100 my-1" />
                  <div className="px-4 py-2 bg-purple-50">
                    <div className="flex items-center space-x-2">
                      <Shield className="w-4 h-4 text-purple-600" />
                      <span className="text-xs font-medium text-purple-600">Super Admin</span>
                    </div>
                    <p className="text-xs text-purple-500 mt-1">Full system access</p>
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
