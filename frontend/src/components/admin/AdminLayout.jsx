import { useCallback, useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import AdminNavbar from "./AdminNavbar";
import AdminSidebar from "./AdminSidebar";
import AdminChatbot from "./AdminChatbot";
import "./AdminPages.css";

/**
 * Admin Layout Wrapper
 * Provides consistent layout for all admin pages with sidebar and navbar
 */

const AdminLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(
    () => window.matchMedia("(min-width: 1024px)").matches,
  );

  const toggleSidebar = () => {
    setSidebarOpen((open) => !open);
  };

  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)");
    media.addEventListener("change", closeSidebar);
    return () => media.removeEventListener("change", closeSidebar);
  }, [closeSidebar]);

  return (
    <div className="admin-shell min-h-screen bg-surface">
      {/* Admin Navbar */}
      <AdminNavbar onMenuToggle={toggleSidebar} sidebarOpen={sidebarOpen} />

      {/* Main Layout */}
      <div className="flex">
        {/* Sidebar */}
        <AdminSidebar
          isOpen={sidebarOpen}
          onToggle={toggleSidebar}
          onClose={closeSidebar}
        />

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 min-h-[calc(100vh-4rem)]">
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
