import { RefreshCw } from "lucide-react";

function QueryFeedback({ query }) {
  if (!query) return null;
  if (query.isPending)
    return (
      <p role="status" className="admin-notice">
        Loading live data…
      </p>
    );
  if (!query.isError) return null;
  return (
    <div role="alert" className="admin-notice admin-error">
      <strong>Data unavailable.</strong> {query.error.message}{" "}
      {query.data && "Showing the last successful response."}
      <button className="admin-button" onClick={() => query.refetch()}>
        Retry
      </button>
    </div>
  );
}

function LastReceived({ query }) {
  if (!query || !query.dataUpdatedAt) return null;
  return (
    <p className="admin-updated">
      Last received {new Date(query.dataUpdatedAt).toLocaleString()}
    </p>
  );
}

export default function AdminPage({ title, description, query, children }) {
  return (
    <section className="admin-page">
      <header className="admin-page-heading">
        <div>
          <p className="admin-eyebrow">FootballHeritage / Administration</p>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        {query && (
          <button
            className="admin-button"
            onClick={() => query.refetch()}
            disabled={query.isFetching}
          >
            <RefreshCw size={16} />
            {query.isFetching ? "Refreshing…" : "Refresh"}
          </button>
        )}
      </header>
      <QueryFeedback query={query} />
      {children}
      <LastReceived query={query} />
    </section>
  );
}

export function AdminMetrics({ items }) {
  return (
    <div className="admin-metrics">
      {items.map(([label, value]) => (
        <article key={label}>
          <p>{label}</p>
          <strong>{value ?? "—"}</strong>
        </article>
      ))}
    </div>
  );
}

export function AdminTable({ columns, rows, empty = "No records available." }) {
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {columns.map((column) => (
                <td key={column.key}>
                  {column.render ? column.render(row) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && <p className="admin-empty">{empty}</p>}
    </div>
  );
}
