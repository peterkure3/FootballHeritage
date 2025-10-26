import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import useAuthStore from '../stores/authStore';
import useSettingsStore from '../stores/settingsStore.js';
import { Settings, Shield, Bell, Database, Mail, MessageSquare, Sparkles } from 'lucide-react';

const AdminSettings = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { chatbotEnabled, toggleChatbot } = useSettingsStore();

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
          <h1 className="text-2xl font-bold text-white">System Settings</h1>
          <p className="text-gray-400 mt-1 text-sm">Configure platform settings</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* AI Assistant Settings */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Sparkles className="w-6 h-6 text-green-400" />
              <h2 className="text-lg font-semibold text-white">AI Assistant</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <MessageSquare className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-300">Admin Chatbot</span>
                </div>
                <button
                  onClick={() => {
                    toggleChatbot();
                    toast.success(chatbotEnabled ? 'Chatbot disabled' : 'Chatbot enabled');
                  }}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    chatbotEnabled ? 'bg-green-500' : 'bg-gray-600'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      chatbotEnabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
              <p className="text-xs text-gray-500">
                Toggle the floating AI assistant that helps with admin tasks and insights
              </p>
            </div>
          </div>

          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Shield className="w-6 h-6 text-green-400" />
              <h2 className="text-lg font-semibold text-white">Security</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">Two-Factor Authentication</span>
                <button className="px-3 py-1 bg-green-500 text-white rounded text-sm">Enabled</button>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">Session Timeout</span>
                <span className="text-sm text-gray-400">30 minutes</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Bell className="w-6 h-6 text-blue-400" />
              <h2 className="text-lg font-semibold text-white">Notifications</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">Email Alerts</span>
                <button className="px-3 py-1 bg-green-500 text-white rounded text-sm">On</button>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">Fraud Alerts</span>
                <button className="px-3 py-1 bg-green-500 text-white rounded text-sm">On</button>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Database className="w-6 h-6 text-purple-400" />
              <h2 className="text-lg font-semibold text-white">Database</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">Last Backup</span>
                <span className="text-sm text-gray-400">2 hours ago</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">Auto Backup</span>
                <button className="px-3 py-1 bg-green-500 text-white rounded text-sm">Daily</button>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Mail className="w-6 h-6 text-orange-400" />
              <h2 className="text-lg font-semibold text-white">Email</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">SMTP Server</span>
                <span className="text-sm text-green-400">Connected</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">Daily Limit</span>
                <span className="text-sm text-gray-400">10,000</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminSettings;
