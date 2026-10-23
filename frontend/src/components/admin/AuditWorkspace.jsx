import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminService } from "../../services/adminService";
import AdminPage, { AdminTable } from "./AdminPage";

const columns = [
  {
    key: "created_at",
    label: "Recorded",
    render: (row) =>
      row.created_at ? new Date(row.created_at).toLocaleString() : "—",
  },
  { key: "admin_email", label: "Administrator" },
  { key: "action", label: "Action" },
  {
    key: "target_type",
    label: "Target",
    render: (row) => (
      <>
        {row.target_type || "—"}
        <small>{row.target_id}</small>
      </>
    ),
  },
];

function FraudAlerts() {
  const query = useQuery({
    queryKey: ["admin-fraud-alerts"],
    queryFn: ({ signal }) => adminService.alerts(signal),
    retry: false,
    refetchInterval: 60000,
  });
  return (
    <section className="admin-panel" aria-label="Pending fraud alerts">
      <h2>Pending alerts</h2>
      {query.isPending && <p role="status">Loading alerts…</p>}
      {query.isError && (
        <div role="alert">
          {query.error.message}
          <button className="admin-button" onClick={() => query.refetch()}>
            Retry alerts
          </button>
        </div>
      )}
      {query.data && (
        <>
          {query.data.alerts.map((alert) => (
            <p key={alert.id}>
              <strong>
                {alert.severity} · {alert.alert_type}
              </strong>{" "}
              — {alert.description}
            </p>
          ))}
          {!query.data.alerts.length && <p>No pending alerts returned.</p>}
        </>
      )}
    </section>
  );
}

export default function AuditWorkspace() {
  const [search, setSearch] = useState("");
  const query = useQuery({
    queryKey: ["admin-audit-logs"],
    queryFn: ({ signal }) => adminService.logs(signal),
    retry: false,
    refetchInterval: 60000,
  });
  const rows = (query.data?.logs || []).filter((row) =>
    [row.admin_email, row.action, row.target_type, row.target_id]
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <AdminPage
      title="Audit activity."
      description="The latest 100 administrator actions recorded by the backend."
      query={query}
    >
      <div className="admin-toolbar">
        <label>
          Search audit logs
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Administrator, action, or target"
          />
        </label>
        <span className="admin-updated">{rows.length} matching records</span>
      </div>
      {query.data && (
        <AdminTable
          columns={columns}
          rows={rows}
          empty={
            search
              ? "No actions match your search."
              : "No administrator actions recorded."
          }
        />
      )}
      <FraudAlerts />
    </AdminPage>
  );
}
