import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Dialog, DataState } from "../../heritage/ui";
import { apiFetch } from '../../utils/api';

export default function TeamEditor({ team, apiUrl, onSave, onClose }) {
  const [squad, setSquad] = useState(() => [
    ...team.starting_xi,
    ...team.bench,
  ]);
  const [starters, setStarters] = useState(() =>
    team.starting_xi.map((player) => player.id),
  );
  const [captain, setCaptain] = useState(team.captain.id);
  const [viceCaptain, setViceCaptain] = useState(team.vice_captain.id);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const catalog = useQuery({
    queryKey: ["fpl-editor-players", apiUrl],
    queryFn: async () => {
      const response = await apiFetch(`${apiUrl}/fpl/players?limit=2000`);
      if (!response.ok)
        throw new Error("Could not load players. Please retry.");
      const players = await response.json();
      if (!Array.isArray(players))
        throw new Error("The player catalog is unavailable.");
      return players;
    },
    staleTime: 0,
    retry: false,
  });
  const playersById = new Map(
    (catalog.data || []).map((player) => [player.id, player]),
  );
  const currentSquad = squad.map(
    (player) => playersById.get(player.id) || player,
  );
  const cost =
    currentSquad.reduce(
      (sum, player) => sum + Math.round(player.price * 10),
      0,
    ) / 10;
  function replacePlayer(oldId, newId) {
    const replacement = playersById.get(Number(newId));
    if (!replacement) return;
    setSquad((current) =>
      current.map((player) => (player.id === oldId ? replacement : player)),
    );
    setStarters((current) =>
      current.map((id) => (id === oldId ? replacement.id : id)),
    );
    if (captain === oldId) setCaptain(replacement.id);
    if (viceCaptain === oldId) setViceCaptain(replacement.id);
    setError("");
  }
  async function save() {
    setSaving(true);
    setError("");
    try {
      const response = await apiFetch(`${apiUrl}/fpl/team/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          squad_ids: squad.map((player) => player.id),
          starter_ids: starters,
          captain_id: captain,
          vice_captain_id: viceCaptain,
        }),
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Could not validate this team. Please try again.",
        );
      onSave(result);
    } catch (err) {
      setError(err.message || "Could not save your team.");
    } finally {
      setSaving(false);
    }
  }
  return (
    <Dialog
      title="Edit team"
      onClose={saving ? () => {} : onClose}
      className="fpl-editor"
    >
      <p className="fh-muted">
        Edit your advisor squad. Saved for this account and gameweek in this
        browser; changes are not submitted to official FPL.
      </p>
      <p className="fh-muted">
        £100m budget · 2 GKP / 5 DEF / 5 MID / 3 FWD · Maximum 3 players per
        club. Select 11 starters, including one goalkeeper.
      </p>
      {catalog.isPending ? (
        <DataState loading />
      ) : catalog.isError ? (
        <DataState error={catalog.error} retry={() => catalog.refetch()} />
      ) : (
        <>
          <div className="fpl-editor-summary" aria-live="polite">
            <strong>Cost: £{cost.toFixed(1)}m</strong>
            <span>Remaining: £{(100 - cost).toFixed(1)}m</span>
            <span>Starters: {starters.length}/11</span>
          </div>
          <label className="fpl-editor-search">
            Find replacements
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search player or club"
              disabled={saving}
            />
          </label>
          <fieldset disabled={saving} className="fpl-editor-fields">
            {currentSquad.map((player, index) => {
              const options = (catalog.data || []).filter(
                (candidate) =>
                  candidate.position === player.position &&
                  !squad.some((selected) => selected.id === candidate.id) &&
                  `${candidate.web_name} ${candidate.team_name}`
                    .toLowerCase()
                    .includes(search.toLowerCase()),
              );
              return (
                <div className="fpl-editor-row" key={index}>
                  <label>
                    <span>
                      {player.position} · {player.web_name}
                    </span>
                    <select
                      aria-label={`Replace ${player.web_name}`}
                      value={player.id}
                      onChange={(event) =>
                        replacePlayer(player.id, event.target.value)
                      }
                    >
                      <option value={player.id}>
                        {player.web_name} · {player.team_name} · £
                        {Number(player.price).toFixed(1)}m
                      </option>
                      {options.map((candidate) => (
                        <option key={candidate.id} value={candidate.id}>
                          {candidate.web_name} · {candidate.team_name} · £
                          {Number(candidate.price).toFixed(1)}m
                          {candidate.status !== "a"
                            ? ` (${candidate.status})`
                            : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="fpl-starter-toggle">
                    <input
                      type="checkbox"
                      checked={starters.includes(player.id)}
                      onChange={(event) => {
                        setStarters((current) =>
                          event.target.checked
                            ? [...current, player.id]
                            : current.filter((id) => id !== player.id),
                        );
                        if (!event.target.checked && captain === player.id)
                          setCaptain(0);
                        if (!event.target.checked && viceCaptain === player.id)
                          setViceCaptain(0);
                      }}
                    />
                    Start {player.web_name}
                  </label>
                </div>
              );
            })}
            <div className="fpl-editor-captains">
              <label>
                Captain
                <select
                  value={captain}
                aria-label="Captain"
                  onChange={(event) => setCaptain(Number(event.target.value))}
                >
                  <option value="">Choose captain</option>
                  {currentSquad
                    .filter((player) => starters.includes(player.id))
                    .map((player) => (
                      <option key={player.id} value={player.id}>
                        {player.web_name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Vice-captain
                <select
                  value={viceCaptain}
                aria-label="Vice-captain"
                  onChange={(event) =>
                    setViceCaptain(Number(event.target.value))
                  }
                >
                  <option value="">Choose vice-captain</option>
                  {currentSquad
                    .filter((player) => starters.includes(player.id))
                    .map((player) => (
                      <option key={player.id} value={player.id}>
                        {player.web_name}
                      </option>
                    ))}
                </select>
              </label>
            </div>
          </fieldset>
        </>
      )}
      {error && (
        <p className="fh-error fpl-editor-error" role="alert">
          {error}
        </p>
      )}
      <div className="fpl-editor-actions">
        <button
          className="fh-button fh-button-secondary"
          onClick={onClose}
          disabled={saving}
        >
          Cancel
        </button>
        <button
          className="fh-button"
          onClick={save}
          disabled={saving || !catalog.isSuccess}
        >
          {saving ? "Saving..." : "Save team"}
        </button>
      </div>
    </Dialog>
  );
}
