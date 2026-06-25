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

  const [profileForm, setProfileForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    address: ''
  });

  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

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

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error('New passwords do not match');
      return;
    }

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
    <div className="min-h-screen" style={{ background: "var(--color-surface)" }}>
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div style={{ animation: 'slide-up 0.4s ease-out both' }}>
          <h1 className="text-3xl md:text-4xl font-bold text-white font-[Oswald] tracking-tight mb-1">
            My Profile
          </h1>
          <p className="text-sm" style={{ color: '#64748b' }}>
            Manage your account information and settings
          </p>
        </div>

        {isLoading ? (
          <LoadingSkeleton type="card" count={2} />
        ) : (
          <>
            {/* Profile Information Card */}
            <div className="card-glow rounded-xl p-6 mt-8 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)', animation: 'slide-up 0.4s ease-out 0.06s both' }}>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white font-[Oswald] tracking-tight">Personal Information</h2>
                {!isEditing && (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="flex items-center gap-2 text-white px-4 py-2 rounded-lg font-semibold text-sm transition-all hover:opacity-90"
                    style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
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
                    <label className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>Email Address</label>
                    <div className="rounded-lg px-4 py-3" style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', color: '#64748b' }}>
                      {user?.email}
                    </div>
                    <p className="text-xs mt-1" style={{ color: '#64748b' }}>Email cannot be changed</p>
                  </div>

                  {/* Date of Birth (Read-only) */}
                  <div>
                    <label className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>Date of Birth</label>
                    <div className="rounded-lg px-4 py-3" style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)', color: '#64748b' }}>
                      {user?.date_of_birth || 'Not set'}
                    </div>
                    <p className="text-xs mt-1" style={{ color: '#64748b' }}>Cannot be modified</p>
                  </div>

                  {/* First Name */}
                  <div>
                    <label className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>First Name</label>
                    <input
                      type="text"
                      name="first_name"
                      value={profileForm.first_name}
                      onChange={handleProfileChange}
                      disabled={!isEditing}
                      className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                      style={{
                        background: 'var(--color-card)',
                        border: `1px solid ${isEditing ? 'var(--color-card-border-hover)' : 'var(--color-card-border)'}`,
                        opacity: isEditing ? 1 : 0.6,
                        '--tw-ring-color': '#10b981',
                      }}
                      placeholder="Enter first name"
                    />
                  </div>

                  {/* Last Name */}
                  <div>
                    <label className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>Last Name</label>
                    <input
                      type="text"
                      name="last_name"
                      value={profileForm.last_name}
                      onChange={handleProfileChange}
                      disabled={!isEditing}
                      className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                      style={{
                        background: 'var(--color-card)',
                        border: `1px solid ${isEditing ? 'var(--color-card-border-hover)' : 'var(--color-card-border)'}`,
                        opacity: isEditing ? 1 : 0.6,
                        '--tw-ring-color': '#10b981',
                      }}
                      placeholder="Enter last name"
                    />
                  </div>

                  {/* Phone */}
                  <div>
                    <label className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>Phone Number</label>
                    <input
                      type="tel"
                      name="phone"
                      value={profileForm.phone}
                      onChange={handleProfileChange}
                      disabled={!isEditing}
                      className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                      style={{
                        background: 'var(--color-card)',
                        border: `1px solid ${isEditing ? 'var(--color-card-border-hover)' : 'var(--color-card-border)'}`,
                        opacity: isEditing ? 1 : 0.6,
                        '--tw-ring-color': '#10b981',
                      }}
                      placeholder="+1 (555) 123-4567"
                    />
                  </div>

                  {/* Address */}
                  <div className="md:col-span-2">
                    <label className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>Address</label>
                    <input
                      type="text"
                      name="address"
                      value={profileForm.address}
                      onChange={handleProfileChange}
                      disabled={!isEditing}
                      className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                      style={{
                        background: 'var(--color-card)',
                        border: `1px solid ${isEditing ? 'var(--color-card-border-hover)' : 'var(--color-card-border)'}`,
                        opacity: isEditing ? 1 : 0.6,
                        '--tw-ring-color': '#10b981',
                      }}
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
                      className="flex-1 text-white px-6 py-3 rounded-lg font-semibold text-sm transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                      style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
                    >
                      {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                    <button
                      type="button"
                      onClick={cancelEdit}
                      disabled={isSaving}
                      className="flex-1 text-white px-6 py-3 rounded-lg font-semibold text-sm transition-all card-glow disabled:opacity-50 disabled:cursor-not-allowed"
                      style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }}
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </form>
            </div>

            {/* Account Status Card */}
            <div className="card-glow rounded-xl p-6 mt-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)', animation: 'slide-up 0.4s ease-out 0.1s both' }}>
              <h2 className="text-xl font-bold text-white font-[Oswald] tracking-tight mb-4">Account Status</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center justify-between rounded-lg p-4" style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }}>
                  <span style={{ color: '#94a3b8' }}>Verification Status</span>
                  <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                    user?.is_verified
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {user?.is_verified ? 'Verified' : 'Pending'}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-lg p-4" style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }}>
                  <span style={{ color: '#94a3b8' }}>Member Since</span>
                  <span className="text-white font-semibold">
                    {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            {/* Security Card */}
            <div className="card-glow rounded-xl p-6 mt-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)', animation: 'slide-up 0.4s ease-out 0.14s both' }}>
              <h2 className="text-xl font-bold text-white font-[Oswald] tracking-tight mb-4">Security</h2>
              <div className="flex items-center justify-between rounded-lg p-4" style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }}>
                <div>
                  <h3 className="text-white font-semibold mb-1">Password</h3>
                  <p className="text-sm" style={{ color: '#64748b' }}>Change your account password</p>
                </div>
                <button
                  onClick={() => setShowPasswordModal(true)}
                  className="text-white px-4 py-2 rounded-lg font-semibold text-sm transition-all hover:opacity-90"
                  style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}
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
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" style={{ animation: 'fade-in 0.2s ease-out' }}>
          <div className="card-glow rounded-xl p-6 max-w-md w-full border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)', animation: 'scale-in 0.2s ease-out' }}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white font-[Oswald] tracking-tight">Change Password</h3>
              <button
                onClick={() => setShowPasswordModal(false)}
                className="transition-colors" style={{ color: '#64748b' }}
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
                  <label className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>Current Password</label>
                  <input
                    type="password"
                    name="current_password"
                    value={passwordForm.current_password}
                    onChange={handlePasswordChange}
                    required
                    className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                    style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border-hover)', '--tw-ring-color': '#6366f1' }}
                    placeholder="Enter current password"
                  />
                </div>

                {/* New Password */}
                <div>
                  <label className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>New Password</label>
                  <input
                    type="password"
                    name="new_password"
                    value={passwordForm.new_password}
                    onChange={handlePasswordChange}
                    required
                    minLength={8}
                    className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                    style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border-hover)', '--tw-ring-color': '#6366f1' }}
                    placeholder="Enter new password (min 8 characters)"
                  />
                </div>

                {/* Confirm Password */}
                <div>
                  <label className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>Confirm New Password</label>
                  <input
                    type="password"
                    name="confirm_password"
                    value={passwordForm.confirm_password}
                    onChange={handlePasswordChange}
                    required
                    minLength={8}
                    className="w-full rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 transition-all"
                    style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border-hover)', '--tw-ring-color': '#6366f1' }}
                    placeholder="Confirm new password"
                  />
                </div>

                {/* Password Requirements */}
                <div className="rounded-lg p-3 border" style={{ background: 'rgba(99, 102, 241, 0.08)', borderColor: 'rgba(99, 102, 241, 0.3)' }}>
                  <p className="text-xs font-semibold mb-2" style={{ color: '#a5b4fc' }}>Password Requirements:</p>
                  <ul className="text-xs space-y-1" style={{ color: '#c7d2fe' }}>
                    <li>At least 8 characters long</li>
                    <li>Mix of letters, numbers, and symbols recommended</li>
                  </ul>
                </div>
              </div>

              {/* Modal Actions */}
              <div className="flex gap-3 mt-6">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="flex-1 text-white px-6 py-3 rounded-lg font-semibold text-sm transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}
                >
                  {isSaving ? 'Changing...' : 'Change Password'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  disabled={isSaving}
                  className="flex-1 text-white px-6 py-3 rounded-lg font-semibold text-sm transition-all card-glow disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: 'var(--color-card)', border: '1px solid var(--color-card-border)' }}
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
