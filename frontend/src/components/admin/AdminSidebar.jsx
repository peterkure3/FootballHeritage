import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Calendar, 
  Dice3, 
  Users, 
  BarChart3, 
  DollarSign,
  Settings,
  FileText,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import './AdminSidebar.css';

/**
 * Admin Sidebar Navigation
 * Left sidebar for admin panel with collapsible menu
 */

const AdminSidebar = ({ isOpen, onToggle }) => {
  const menuSections = [
    {
      title: 'OVERVIEW',
      items: [
        { path: '/admin/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
      ]
    },
    {
      title: 'MANAGEMENT',
      items: [
        { path: '/admin/events', icon: Calendar, label: 'Events' },
        { path: '/admin/bets', icon: Dice3, label: 'Bets' },
        { path: '/admin/users', icon: Users, label: 'Users' },
      ]
    },
    {
      title: 'ANALYTICS',
      items: [
        { path: '/admin/analytics', icon: BarChart3, label: 'Statistics' },
        { path: '/admin/revenue', icon: DollarSign, label: 'Revenue' },
      ]
    },
    {
      title: 'SYSTEM',
      items: [
        { path: '/admin/settings', icon: Settings, label: 'Settings' },
        { path: '/admin/logs', icon: FileText, label: 'Audit Logs' },
      ]
    }
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:sticky top-0 left-0 h-screen bg-slate-800 border-r border-slate-700 z-50
        transition-all duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        ${isOpen ? 'w-64' : 'w-64 lg:w-20'}
      `}>
        <div className="flex flex-col h-full">
          {/* Sidebar Header */}
          <div className="h-16 flex items-center justify-between px-4 border-b border-slate-700">
            {isOpen && (
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">FH</span>
                </div>
                <span className="text-white font-semibold">Admin Panel</span>
              </div>
            )}
            <button
              onClick={onToggle}
              className="hidden lg:flex p-2 hover:bg-slate-700 rounded-lg transition-colors text-gray-400 hover:text-white"
            >
              {isOpen ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            </button>
          </div>

          {/* Navigation Menu */}
          <nav 
            className="admin-sidebar-nav flex-1 overflow-y-auto py-4 px-2"
            style={{
              scrollbarWidth: 'thin',
              scrollbarColor: '#475569 #1e293b'
            }}
          >
            {menuSections.map((section, idx) => (
              <div key={idx} className="mb-6">
                {isOpen && (
                  <h3 className="px-3 mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    {section.title}
                  </h3>
                )}
                <div className="space-y-1">
                  {section.items.map((item) => (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      className={({ isActive }) => `
                        flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all
                        ${isActive 
                          ? 'bg-green-500 text-white shadow-lg shadow-green-500/20' 
                          : 'text-gray-400 hover:bg-slate-700 hover:text-white'
                        }
                        ${!isOpen && 'justify-center'}
                      `}
                      title={!isOpen ? item.label : ''}
                    >
                      <item.icon className="w-5 h-5 flex-shrink-0" />
                      {isOpen && <span className="font-medium">{item.label}</span>}
                    </NavLink>
                  ))}
                </div>
              </div>
            ))}
          </nav>

          {/* Sidebar Footer */}
          <div className="p-4 border-t border-slate-700">
            {isOpen ? (
              <div className="bg-slate-900 rounded-lg p-3">
                <p className="text-xs text-gray-400 mb-1">Admin Mode</p>
                <p className="text-sm text-white font-medium">Full Access</p>
              </div>
            ) : (
              <div className="w-8 h-8 bg-green-500 rounded-full mx-auto" />
            )}
          </div>
        </div>
      </aside>
    </>
  );
};

export default AdminSidebar;
