export default function QueryState({
  query,
  children,
  loading = "Loading…",
  failure = "Data unavailable",
  showRefresh = false,
}) {
  return (
    <>
      {showRefresh && query.data !== undefined && (
        <p className="pd-muted" role="status">
          Saved public data from {new Date(query.dataUpdatedAt).toLocaleTimeString()}.
          {query.isFetching ? " Refreshing…" : query.error ? " Refresh failed; showing the last loaded data." : ""}
        </p>
      )}
      {query.isPending && (
        <p className="pd-loading" role="status">
          {loading}
        </p>
      )}
      {query.error && (
        <div className="pd-notice" role="alert">
          {failure}: {query.error.message}{" "}
          <button
            className="pd-button pd-button-outline"
            onClick={() => void query.refetch()}
          >
            Retry
          </button>
        </div>
      )}
      {query.data !== undefined && children(query.data)}
    </>
  );
}
