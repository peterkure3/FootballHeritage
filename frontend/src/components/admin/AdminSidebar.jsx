import { useEffect, useRef } from "react";
import { NavLink } from "react-router-dom";
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
  ChevronRight,
  Sparkles,
  X,
  Activity,
  FlaskConical,
  Layers,
} from "lucide-react";
import useAuthStore from "../../stores/authStore";
import "./AdminSidebar.css";

const sections = [
  {
    title: "Operations",
    items: [
      {
        path: "/admin/dashboard",
        icon: LayoutDashboard,
        label: "Live overview",
      },
      {
        path: "/predictions?view=comparisons",
        icon: Layers,
        label: "Sportsbook odds",
      },
      {
        path: "/predictions?view=fixtures",
        icon: Activity,
        label: "Probabilities & EV",
      },
      {
        path: "/predictions?view=trials",
        icon: FlaskConical,
        label: "Paper trials",
      },
    ],
  },
  {
    title: "Platform",
    items: [
      { path: "/admin/events", icon: Calendar, label: "Events" },
      { path: "/admin/bets", icon: Dice3, label: "Bets" },
      { path: "/admin/users", icon: Users, label: "Users" },
      { path: "/admin/analytics", icon: BarChart3, label: "Statistics" },
      { path: "/admin/revenue", icon: DollarSign, label: "Revenue" },
    ],
  },
  {
    title: "Workspace",
    items: [
      { path: "/admin/sportsgpt", icon: Sparkles, label: "SportsGPT" },
      { path: "/admin/logs", icon: FileText, label: "Audit activity" },
      { path: "/admin/settings", icon: Settings, label: "Preferences" },
      { path: "/admin/features", icon: Settings, label: "Feature Management" },
    ],
  },
];

function NavigationSection({ section, expanded, onNavigate }) {
  return (
    <section className="admin-sidebar-section">
      <h2>
        {expanded ? (
          section.title
        ) : (
          <span className="sr-only">{section.title}</span>
        )}
      </h2>
      {section.items.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          onClick={onNavigate}
          aria-label={item.label}
          title={expanded ? undefined : item.label}
          className={({ isActive }) =>
            `admin-sidebar-link${isActive ? " active" : ""}`
          }
        >
          <item.icon size={19} aria-hidden="true" />
          {expanded && <span>{item.label}</span>}
        </NavLink>
      ))}
    </section>
  );
}

function useDrawerFocus(sidebar, isOpen, onClose) {
  useEffect(() => {
    if (!isOpen || window.matchMedia("(min-width: 1024px)").matches) return;
    const previous = document.activeElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    sidebar.current.querySelector(".admin-sidebar-close").focus();
    function keyboard(event) {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab") return;
      const controls = [...sidebar.current.querySelectorAll("a,button")].filter(
        (node) => node.getClientRects().length,
      );
      const first = controls[0],
        last = controls.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", keyboard);
    return () => {
      document.body.style.overflow = overflow;
      document.removeEventListener("keydown", keyboard);
      previous?.focus();
    };
  }, [sidebar, isOpen, onClose]);
}

function SidebarAccount({ expanded }) {
  const user = useAuthStore((state) => state.user) || {};
  const firstName = user.first_name || "Admin";
  return (
    <footer className="admin-sidebar-footer">
      <span className="admin-sidebar-avatar">{firstName[0]}</span>
      {expanded && (
        <div>
          <strong>{firstName}</strong>
          <small>
            {user.is_super_admin ? "Super administrator" : "Administrator"}
          </small>
        </div>
      )}
    </footer>
  );
}

export default function AdminSidebar({ isOpen, onToggle, onClose }) {
  const sidebar = useRef(null);
  useDrawerFocus(sidebar, isOpen, onClose);
  function navigate() {
    if (!window.matchMedia("(min-width: 1024px)").matches) onClose();
  }
  return (
    <>
      {isOpen && (
        <button
          className="admin-sidebar-backdrop"
          onClick={onClose}
          aria-label="Close admin navigation"
          tabIndex={-1}
        />
      )}
      <aside
        ref={sidebar}
        id="admin-sidebar"
        className={`admin-sidebar ${isOpen ? "expanded" : "collapsed"}`}
      >
        <header className="admin-sidebar-brand">
          {isOpen && (
            <div>
              <b>
                FH<span> / ADMIN</span>
              </b>
              <p>Operations workspace</p>
            </div>
          )}
          <button
            className="admin-sidebar-collapse"
            onClick={onToggle}
            aria-label={isOpen ? "Collapse sidebar" : "Expand sidebar"}
            aria-expanded={isOpen}
          >
            {isOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
          </button>
          <button
            className="admin-sidebar-close"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
        </header>
        <nav className="admin-sidebar-nav" aria-label="Admin navigation">
          {sections.map((section) => (
            <NavigationSection
              key={section.title}
              section={section}
              expanded={isOpen}
              onNavigate={navigate}
            />
          ))}
        </nav>
        <SidebarAccount expanded={isOpen} />
      </aside>
    </>
  );
}
