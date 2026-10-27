import { Dialog } from "../heritage/ui";
import { History, ArrowLeft, ArrowRight, ShieldCheck } from "lucide-react";

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
    <section
      className="feature-history"
      id="feature-audit-history"
      aria-labelledby="feature-history-title"
    >
      <div className="feature-section-heading">
        <div>
          <History size={19} aria-hidden="true" />
          <h2 id="feature-history-title">Audit history</h2>
        </div>
        <span className="feature-history-label">Change log</span>
      </div>
      <p className="feature-history-description">
        A record of who changed access, what changed, and when.
      </p>
      {loading && <p role="status">Loading audit history…</p>}
      <div
        className="feature-audit"
        role="region"
        aria-label="Feature change records"
        tabIndex={0}
      >
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
      {!loading && rows.length === 0 && (
        <div className="feature-history-empty">
          <ShieldCheck size={24} aria-hidden="true" />
          <strong>No changes recorded.</strong>
          <p>Confirmed feature updates will appear here.</p>
        </div>
      )}
      <div className="feature-history-footer">
        <span>
          {loading
            ? "Loading records…"
            : `${rows.length} ${rows.length === 1 ? "record" : "records"} on this page`}
        </span>
        <div>
          <button
            className="admin-button"
            disabled={!before || loading}
            onClick={() => setBefore(null)}
          >
            <ArrowLeft size={14} aria-hidden="true" /> Newest
          </button>{" "}
          <button
            className="admin-button"
            disabled={rows.length !== 100 || loading}
            onClick={() => setBefore(rows.at(-1).id)}
          >
            Older changes <ArrowRight size={14} aria-hidden="true" />
          </button>
        </div>
      </div>
    </section>
  );
}

export function FeatureConfirmation({ pending, mutation, cancel }) {
  if (!pending) return null;
  return (
    <Dialog title={pending.title} onClose={cancel}>
      <div className="feature-confirmation">
        <span className="feature-confirm-icon">
          <ShieldCheck size={24} aria-hidden="true" />
        </span>
        <h2>{pending.title}?</h2>
        <p>
          This may immediately restrict live operations. Every change is
          audited.
        </p>
        {mutation.isError && <p role="alert">{mutation.error.message}</p>}
        <div className="feature-confirm-actions">
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
        </div>
      </div>
    </Dialog>
  );
}

export function FeatureErrors({ queries }) {
  return queries
    .filter((q) => q.isError)
    .map((q, i) => (
      <p className="feature-feedback error" role="alert" key={i}>
        {q.error.message}{" "}
        <button className="admin-button" onClick={() => q.refetch()}>
          Retry
        </button>
      </p>
    ));
}
