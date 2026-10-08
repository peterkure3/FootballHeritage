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
          <h1 className="text-2xl font-bold text-heritage-ink">System Settings</h1>
          <p className="text-heritage-muted mt-1 text-sm">Configure platform settings</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* AI Assistant Settings */}
          <div className="bg-card rounded-xl border border-card-border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Sparkles className="w-6 h-6 text-green-700" />
              <h2 className="text-lg font-semibold text-heritage-ink">AI Assistant</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <MessageSquare className="w-4 h-4 text-heritage-muted" />
                  <span className="text-sm text-heritage-ink">Admin Chatbot</span>
                </div>
                <button
                  onClick={() => {
                    toggleChatbot();
                    toast.success(chatbotEnabled ? 'Chatbot disabled' : 'Chatbot enabled');
                  }}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    chatbotEnabled ? 'bg-green-500' : 'bg-card-hover'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      chatbotEnabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
              <p className="text-xs text-heritage-muted">
                Toggle the floating AI assistant that helps with admin tasks and insights
              </p>
            </div>
          </div>

          <div className="bg-card rounded-xl border border-card-border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Shield className="w-6 h-6 text-green-700" />
              <h2 className="text-lg font-semibold text-heritage-ink">Security</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-heritage-ink">Two-Factor Authentication</span>
                <button className="px-3 py-1 bg-green-500 text-white rounded text-sm">Enabled</button>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-heritage-ink">Session Timeout</span>
                <span className="text-sm text-heritage-muted">30 minutes</span>
              </div>
            </div>
          </div>

          <div className="bg-card rounded-xl border border-card-border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Bell className="w-6 h-6 text-blue-700" />
              <h2 className="text-lg font-semibold text-heritage-ink">Notifications</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-heritage-ink">Email Alerts</span>
                <button className="px-3 py-1 bg-green-500 text-white rounded text-sm">On</button>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-heritage-ink">Fraud Alerts</span>
                <button className="px-3 py-1 bg-green-500 text-white rounded text-sm">On</button>
              </div>
            </div>
          </div>

          <div className="bg-card rounded-xl border border-card-border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Database className="w-6 h-6 text-purple-700" />
              <h2 className="text-lg font-semibold text-heritage-ink">Database</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-heritage-ink">Last Backup</span>
                <span className="text-sm text-heritage-muted">2 hours ago</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-heritage-ink">Auto Backup</span>
                <button className="px-3 py-1 bg-green-500 text-white rounded text-sm">Daily</button>
              </div>
            </div>
          </div>

          <div className="bg-card rounded-xl border border-card-border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Mail className="w-6 h-6 text-orange-700" />
              <h2 className="text-lg font-semibold text-heritage-ink">Email</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-heritage-ink">SMTP Server</span>
                <span className="text-sm text-green-700">Connected</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-heritage-ink">Daily Limit</span>
                <span className="text-sm text-heritage-muted">10,000</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminSettings;
