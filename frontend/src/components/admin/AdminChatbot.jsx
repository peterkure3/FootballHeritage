import { Link, useLocation } from "react-router-dom";
import { Sparkles } from "lucide-react";
import useSettingsStore from "../../stores/settingsStore";

export default function AdminChatbot() {
  const enabled = useSettingsStore((state) => state.chatbotEnabled);
  const location = useLocation();
  if (!enabled || location.pathname === "/admin/sportsgpt") return null;
  return (
    <Link to="/admin/sportsgpt" className="admin-chat-launcher">
      <Sparkles size={16} />
      Ask SportsGPT
    </Link>
  );
}
