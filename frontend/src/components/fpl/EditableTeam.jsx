import { useState } from "react";
import { Pencil, RotateCcw } from "lucide-react";
import TeamEditor from "./TeamEditor";

function readTeam(key) {
  try {
    const saved = JSON.parse(localStorage.getItem(key));
    if (
      saved?.team?.starting_xi?.length === 11 &&
      saved?.team?.bench?.length === 4 &&
      saved.team.captain &&
      saved.team.vice_captain &&
      [...saved.team.starting_xi, ...saved.team.bench].every(
        (player) =>
          player &&
          Number.isInteger(player.id) &&
          typeof player.web_name === "string",
      )
    )
      return saved;
  } catch {
    /* Missing or damaged browser storage falls back to the suggestion. */
  }
  return null;
}

export default function EditableTeam({
  suggested,
  storageKey,
  apiUrl,
  children,
}) {
  const [saved, setSaved] = useState(() => readTeam(storageKey));
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const team = saved?.team || suggested;
  function save(team) {
    const next = { team, savedAt: new Date().toISOString() };
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
    } catch {
      throw new Error(
        "Browser storage is unavailable. Your team could not be saved.",
      );
    }
    setSaved(next);
    setEditing(false);
    setError("");
  }
  function reset() {
    try {
      localStorage.removeItem(storageKey);
      setSaved(null);
      setError("");
    } catch {
      setError(
        "Browser storage is unavailable. Your saved team could not be reset.",
      );
    }
  }
  return (
    <>
      <div className="fh-card fpl-team-toolbar">
        <div>
          <strong>{saved ? "My team" : "Suggested team"}</strong>
          <p className="fh-muted">
            {saved
              ? `Saved in this browser · ${new Date(saved.savedAt).toLocaleString()}. Edit and save to update prices and projections.`
              : "Customize the suggested squad, starting eleven and captain choices."}
          </p>
        </div>
        <div className="fpl-editor-actions">
          <button
            className="fh-button"
            onClick={() => setEditing(true)}
            disabled={!team}
          >
            <Pencil size={15} />
            Edit team
          </button>
          {saved && (
            <button className="fh-button fh-button-secondary" onClick={reset}>
              <RotateCcw size={15} />
              Use suggested team
            </button>
          )}
        </div>
      </div>
      {error && (
        <p role="alert" className="fh-error">
          {error}
        </p>
      )}
      {children(team)}
      {editing && (
        <TeamEditor
          team={team}
          apiUrl={apiUrl}
          onSave={save}
          onClose={() => setEditing(false)}
        />
      )}
    </>
  );
}
