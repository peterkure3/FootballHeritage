import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { adminService } from "../../services/adminService";
import EventFormModal from "../EventFormModal";
import AdminPage, { AdminTable } from "./AdminPage";

function EventFilters({
  sport,
  status,
  changeSport,
  changeStatus,
  search,
  changeSearch,
}) {
  return (
    <div className="admin-toolbar">
      <label>
        Search this page
        <input
          value={search}
          onChange={(event) => changeSearch(event.target.value)}
          placeholder="Team or league"
        />
      </label>
      <label>
        Sport
        <select
          value={sport}
          onChange={(event) => changeSport(event.target.value)}
        >
          <option value="">All sports</option>
          <option value="SOCCER">Soccer</option>
          <option value="BASKETBALL">Basketball</option>
          <option value="TENNIS">Tennis</option>
          <option value="ESPORTS">Esports</option>
        </select>
      </label>
      <label>
        Event status
        <select
          value={status}
          onChange={(event) => changeStatus(event.target.value)}
        >
          <option value="">All statuses</option>
          <option value="UPCOMING">Upcoming</option>
          <option value="LIVE">Live</option>
          <option value="FINISHED">Finished</option>
        </select>
      </label>
    </div>
  );
}

function eventColumns(edit, remove, deleting) {
  return [
    {
      key: "home_team",
      label: "Fixture",
      render: (row) => (
        <>
          {row.home_team} v {row.away_team}
          <small>
            {row.league} · {row.sport}
          </small>
        </>
      ),
    },
    {
      key: "event_date",
      label: "Kickoff",
      render: (row) => new Date(row.event_date).toLocaleString(),
    },
    { key: "status", label: "Status" },
    {
      key: "score",
      label: "Score",
      render: (row) =>
        row.home_score == null || row.away_score == null
          ? "—"
          : `${row.home_score} – ${row.away_score}`,
    },
    {
      key: "actions",
      label: "Actions",
      render: (row) => (
        <div className="admin-actions">
          <button className="admin-button" onClick={() => edit(row)}>
            Edit
          </button>
          <button
            className="admin-button"
            disabled={deleting}
            onClick={() => remove(row)}
          >
            Delete
          </button>
        </div>
      ),
    },
  ];
}

export default function EventsWorkspace() {
  const [sport, setSport] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const query = useQuery({
    queryKey: ["admin-events", sport, status, page],
    queryFn: ({ signal }) =>
      adminService.events(
        {
          ...(sport && { sport }),
          ...(status && { status }),
          limit: 50,
          offset: (page - 1) * 50,
        },
        signal,
      ),
    retry: false,
  });
  const deletion = useMutation({
    mutationFn: (id) => adminService.deleteEvent(id),
    onSuccess: () => query.refetch(),
  });
  const rows = (query.data?.events || []).filter((row) =>
    `${row.home_team} ${row.away_team} ${row.league}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  function remove(row) {
    if (window.confirm(`Delete ${row.home_team} v ${row.away_team}?`))
      deletion.mutate(row.id);
  }
  return (
    <AdminPage
      title="Event management."
      description="Manage fixtures in the betting platform. Search applies to the current page."
      query={query}
    >
      <button className="admin-button" onClick={() => setCreating(true)}>
        Create event
      </button>
      <EventFilters
        sport={sport}
        status={status}
        search={search}
        changeSearch={setSearch}
        changeSport={(value) => {
          setSport(value);
          setPage(1);
        }}
        changeStatus={(value) => {
          setStatus(value);
          setPage(1);
        }}
      />
      {deletion.isError && (
        <p role="alert" className="admin-notice admin-error">
          {deletion.error.message}
        </p>
      )}
      {query.data && (
        <>
          <AdminTable
            columns={eventColumns(setEditing, remove, deletion.isPending)}
            rows={rows}
            empty="No events match these filters."
          />
          <div className="admin-toolbar">
            <button
              className="admin-button"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              Previous events
            </button>
            <span>Page {page}</span>
            <button
              className="admin-button"
              disabled={query.data.events.length < 50}
              onClick={() => setPage(page + 1)}
            >
              Next events
            </button>
          </div>
        </>
      )}
      <EventFormModal
        isOpen={creating || !!editing}
        event={editing}
        onClose={() => {
          setCreating(false);
          setEditing(null);
        }}
        onSuccess={() => query.refetch()}
      />
    </AdminPage>
  );
}
