import { Dialog } from "../heritage/ui";

function AuditRow({ row }) {
  return (
    <tr>
      <td>{row.administrator_id}</td>
      <td>{row.action}</td>
      <td>
        {row.feature_key}
        <br />
        {row.target}
      </td>
      <td>{new Date(row.created_at).toLocaleString()}</td>
      <td>
        <code>
          {JSON.stringify(row.before_value)} → {JSON.stringify(row.after_value)}
        </code>
      </td>
    </tr>
  );
}

export function FeatureHistory({ rows, loading, before, setBefore }) {
  return (
    <>
      <h2>Audit history</h2>
      {loading && <p role="status">Loading audit history…</p>}
      <div className="feature-audit">
        <table>
          <thead>
            <tr>
              <th>Administrator</th>
              <th>Action</th>
              <th>Feature / target</th>
              <th>Timestamp</th>
              <th>Before / after</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <AuditRow key={row.id} row={row} />
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p>No changes recorded.</p>}
      <button
        className="admin-button"
        disabled={!before}
        onClick={() => setBefore(null)}
      >
        Newest
      </button>{" "}
      <button
        className="admin-button"
        disabled={rows.length !== 100}
        onClick={() => setBefore(rows.at(-1).id)}
      >
        Older changes
      </button>
    </>
  );
}

export function FeatureConfirmation({ pending, mutation, cancel }) {
  if (!pending) return null;
  return (
    <Dialog title={pending.title} onClose={cancel}>
      <h2>{pending.title}?</h2>
      <p>
        This may immediately restrict live operations. Every change is audited.
      </p>
      {mutation.isError && <p role="alert">{mutation.error.message}</p>}
      <button
        className="admin-button"
        disabled={mutation.isPending}
        onClick={cancel}
      >
        Cancel
      </button>{" "}
      <button
        className="admin-button"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate(pending)}
      >
        {mutation.isPending ? "Saving…" : "Confirm change"}
      </button>
    </Dialog>
  );
}

export function FeatureErrors({ queries }) {
  return queries
    .filter((q) => q.isError)
    .map((q, i) => (
      <p role="alert" key={i}>
        {q.error.message}{" "}
        <button className="admin-button" onClick={() => q.refetch()}>
          Retry
        </button>
      </p>
    ));
}
