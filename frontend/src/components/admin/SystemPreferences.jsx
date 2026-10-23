import { Link } from "react-router-dom";
import useSettingsStore from "../../stores/settingsStore";
import useAuthStore from "../../stores/authStore";
import AdminPage from "./AdminPage";

export default function SystemPreferences() {
  const { chatbotEnabled, toggleChatbot } = useSettingsStore();
  const user = useAuthStore((state) => state.user);
  return (
    <AdminPage
      title="Admin preferences."
      description="Preferences saved in this browser and links to platform monitoring."
    >
      <article className="admin-panel">
        <h2>Workspace assistant</h2>
        <label className="admin-setting">
          <span>Show the SportsGPT shortcut</span>
          <input
            type="checkbox"
            checked={chatbotEnabled}
            onChange={toggleChatbot}
          />
        </label>
        <p>This preference is saved on this device.</p>
      </article>
      <article className="admin-panel">
        <h2>Your session</h2>
        <p>{user?.email}</p>
        <p>
          Role: {user?.is_super_admin ? "Super administrator" : "Administrator"}
        </p>
        <Link className="admin-button" to="/profile">
          Account and password settings
        </Link>
      </article>
      <article className="admin-panel">
        <h2>System monitoring</h2>
        <p>
          Review collection health, sportsbook coverage, model forecasts, and
          paper trial results in live operations.
        </p>
        <div className="admin-toolbar">
          <Link className="admin-button" to="/admin/dashboard">
            Open operations
          </Link>
          <Link className="admin-button" to="/admin/logs">
            Audit activity
          </Link>
        </div>
      </article>
    </AdminPage>
  );
}
