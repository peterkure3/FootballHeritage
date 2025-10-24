import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../hooks/useAuth';
import useAuthStore from '../stores/authStore';
import { api, tokenManager } from '../utils/api';
import Navbar from '../components/Navbar';
import LoadingSkeleton from '../components/LoadingSkeleton';
import { toast } from 'react-hot-toast';

const Profile = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const { data: user, isLoading, refetch } = useUser();
  
  const [isEditing, setIsEditing] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  // Profile form state
  const [profileForm, setProfileForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    address: ''
  });
  
  // Password form state
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  // Initialize form with user data
  useEffect(() => {
    if (user) {
      setProfileForm({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        phone: user.phone || '',
        address: user.address || ''
      });
    }
  }, [user]);

  if (!isAuthenticated) {
    return null;
  }

  const handleProfileChange = (e) => {
    setProfileForm({
      ...profileForm,
      [e.target.name]: e.target.value
    });
  };

  const handlePasswordChange = (e) => {
    setPasswordForm({
      ...passwordForm,
      [e.target.name]: e.target.value
    });
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);

    try {
      const token = tokenManager.getToken();
      const response = await fetch('http://localhost:8080/api/v1/user/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(profileForm)
      });

      if (!response.ok) {
        throw new Error('Failed to update profile');
      }

      toast.success('Profile updated successfully!');
      setIsEditing(false);
      refetch();
    } catch (error) {
      console.error('Profile update error:', error);
      toast.error('Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();

    // Validate passwords match
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error('New passwords do not match');
      return;
    }

    // Validate password length
    if (passwordForm.new_password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    setIsSaving(true);

    try {
      const token = tokenManager.getToken();
      const response = await fetch('http://localhost:8080/api/v1/user/password', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to change password');
      }

      toast.success('Password changed successfully!');
      setShowPasswordModal(false);
      setPasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
    } catch (error) {
      console.error('Password change error:', error);
      toast.error(error.message || 'Failed to change password');
    } finally {
      setIsSaving(false);
    }
  };

  const cancelEdit = () => {
    setIsEditing(false);
    // Reset form to user data
    if (user) {
      setProfileForm({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        phone: user.phone || '',
        address: user.address || ''
      });
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            My Profile
          </h1>
          <p className="text-gray-400">
            Manage your account information and settings
          </p>
        </div>

        {isLoading ? (
          <LoadingSkeleton type="card" count={2} />
        ) : (
          <>
            {/* Profile Information Card */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6 shadow-xl">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white">Personal Information</h2>
                {!isEditing && (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg font-semibold transition-colors flex items-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    Edit Profile
                  </button>
                )}
              </div>

              <form onSubmit={handleProfileSubmit}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Email (Read-only) */}
                  <div>
                    <label className="block text-gray-400 text-sm font-semibold mb-2">
                      Email Address
                    </label>
                    <div className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-gray-500">
                      {user?.email}
                    </div>
                    <p className="text-gray-500 text-xs mt-1">Email cannot be changed</p>
                  </div>

                  {/* Date of Birth (Read-only) */}
                  <div>
                    <label className="block text-gray-400 text-sm font-semibold mb-2">
                      Date of Birth
                    </label>
                    <div className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-gray-500">
                      {user?.date_of_birth || 'Not set'}
                    </div>
                    <p className="text-gray-500 text-xs mt-1">Cannot be modified</p>
                  </div>

                  {/* First Name */}
                  <div>
                    <label className="block text-gray-400 text-sm font-semibold mb-2">
                      First Name
                    </label>
                    <input
                      type="text"
                      name="first_name"
                      value={profileForm.first_name}
                      onChange={handleProfileChange}
                      disabled={!isEditing}
                      className={`w-full bg-gray-900 border ${isEditing ? 'border-gray-600' : 'border-gray-700'} rounded-lg px-4 py-3 text-white focus:outline-none focus:border-green-500 transition-colors ${!isEditing && 'cursor-not-allowed'}`}
                      placeholder="Enter first name"
                    />
                  </div>

                  {/* Last Name */}
                  <div>
                    <label className="block text-gray-400 text-sm font-semibold mb-2">
                      Last Name
                    </label>
                    <input
                      type="text"
                      name="last_name"
                      value={profileForm.last_name}
                      onChange={handleProfileChange}
                      disabled={!isEditing}
                      className={`w-full bg-gray-900 border ${isEditing ? 'border-gray-600' : 'border-gray-700'} rounded-lg px-4 py-3 text-white focus:outline-none focus:border-green-500 transition-colors ${!isEditing && 'cursor-not-allowed'}`}
                      placeholder="Enter last name"
                    />
                  </div>

                  {/* Phone */}
                  <div>
                    <label className="block text-gray-400 text-sm font-semibold mb-2">
                      Phone Number
                    </label>
                    <input
                      type="tel"
                      name="phone"
                      value={profileForm.phone}
                      onChange={handleProfileChange}
                      disabled={!isEditing}
                      className={`w-full bg-gray-900 border ${isEditing ? 'border-gray-600' : 'border-gray-700'} rounded-lg px-4 py-3 text-white focus:outline-none focus:border-green-500 transition-colors ${!isEditing && 'cursor-not-allowed'}`}
                      placeholder="+1 (555) 123-4567"
                    />
                  </div>

                  {/* Address */}
                  <div className="md:col-span-2">
                    <label className="block text-gray-400 text-sm font-semibold mb-2">
                      Address
                    </label>
                    <input
                      type="text"
                      name="address"
                      value={profileForm.address}
                      onChange={handleProfileChange}
                      disabled={!isEditing}
                      className={`w-full bg-gray-900 border ${isEditing ? 'border-gray-600' : 'border-gray-700'} rounded-lg px-4 py-3 text-white focus:outline-none focus:border-green-500 transition-colors ${!isEditing && 'cursor-not-allowed'}`}
                      placeholder="123 Main St, City, State 12345"
                    />
                  </div>
                </div>

                {/* Edit Actions */}
                {isEditing && (
                  <div className="flex gap-3 mt-6">
                    <button
                      type="submit"
                      disabled={isSaving}
                      className="flex-1 bg-green-500 hover:bg-green-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-semibold transition-colors"
                    >
                      {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                    <button
                      type="button"
                      onClick={cancelEdit}
                      disabled={isSaving}
                      className="flex-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-semibold transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </form>
            </div>

            {/* Account Status Card */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6 shadow-xl">
              <h2 className="text-xl font-bold text-white mb-4">Account Status</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center justify-between bg-gray-900 rounded-lg p-4">
                  <span className="text-gray-400">Verification Status</span>
                  <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                    user?.is_verified
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {user?.is_verified ? '✓ Verified' : 'Pending'}
                  </span>
                </div>
                <div className="flex items-center justify-between bg-gray-900 rounded-lg p-4">
                  <span className="text-gray-400">Member Since</span>
                  <span className="text-white font-semibold">
                    {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            {/* Security Card */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-xl">
              <h2 className="text-xl font-bold text-white mb-4">Security</h2>
              <div className="flex items-center justify-between bg-gray-900 rounded-lg p-4">
                <div>
                  <h3 className="text-white font-semibold mb-1">Password</h3>
                  <p className="text-gray-400 text-sm">••••••••••••</p>
                </div>
                <button
                  onClick={() => setShowPasswordModal(true)}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-semibold transition-colors"
                >
                  Change Password
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Password Change Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white">Change Password</h3>
              <button
                onClick={() => setShowPasswordModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handlePasswordSubmit}>
              <div className="space-y-4">
                {/* Current Password */}
                <div>
                  <label className="block text-gray-400 text-sm font-semibold mb-2">
                    Current Password
                  </label>
                  <input
                    type="password"
                    name="current_password"
                    value={passwordForm.current_password}
                    onChange={handlePasswordChange}
                    required
                    className="w-full bg-gray-900 border border-gray-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
                    placeholder="Enter current password"
                  />
                </div>

                {/* New Password */}
                <div>
                  <label className="block text-gray-400 text-sm font-semibold mb-2">
                    New Password
                  </label>
                  <input
                    type="password"
                    name="new_password"
                    value={passwordForm.new_password}
                    onChange={handlePasswordChange}
                    required
                    minLength={8}
                    className="w-full bg-gray-900 border border-gray-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
                    placeholder="Enter new password (min 8 characters)"
                  />
                </div>

                {/* Confirm Password */}
                <div>
                  <label className="block text-gray-400 text-sm font-semibold mb-2">
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    name="confirm_password"
                    value={passwordForm.confirm_password}
                    onChange={handlePasswordChange}
                    required
                    minLength={8}
                    className="w-full bg-gray-900 border border-gray-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
                    placeholder="Confirm new password"
                  />
                </div>

                {/* Password Requirements */}
                <div className="bg-blue-500/10 border border-blue-500/50 rounded-lg p-3">
                  <p className="text-blue-300 text-xs font-semibold mb-2">Password Requirements:</p>
                  <ul className="text-blue-200 text-xs space-y-1">
                    <li>• At least 8 characters long</li>
                    <li>• Mix of letters, numbers, and symbols recommended</li>
                  </ul>
                </div>
              </div>

              {/* Modal Actions */}
              <div className="flex gap-3 mt-6">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="flex-1 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-semibold transition-colors"
                >
                  {isSaving ? 'Changing...' : 'Change Password'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  disabled={isSaving}
                  className="flex-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-semibold transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile;
