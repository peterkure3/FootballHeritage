import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import AdminNavbar from './AdminNavbar';
import AdminSidebar from './AdminSidebar';
import AdminChatbot from './AdminChatbot';

/**
 * Admin Layout Wrapper
 * Provides consistent layout for all admin pages with sidebar and navbar
 */

const AdminLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Admin Navbar */}
      <AdminNavbar onMenuToggle={toggleSidebar} />

      {/* Main Layout */}
      <div className="flex">
        {/* Sidebar */}
        <AdminSidebar isOpen={sidebarOpen} onToggle={toggleSidebar} />

        {/* Main Content Area */}
        <main className={`
          flex-1 min-h-[calc(100vh-4rem)] transition-all duration-300
          ${sidebarOpen ? 'lg:ml-0' : 'lg:ml-0'}
        `}>
          <div className="p-6 lg:p-8">
            <Outlet />
          </div>
        </main>
      </div>

      {/* AI Chatbot - Floating */}
      <AdminChatbot />
    </div>
  );
};

export default AdminLayout;
