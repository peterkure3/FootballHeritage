# Progressive settled history loading

Settled history requests start before the secondary performance summary and model
version list. Secondary queries become eligible after history succeeds or fails,
so a history error cannot indefinitely suppress the other panels.

An explicit session-storage cache covers only public settled history, aggregate
accuracy and model versions. Keys include all query filters and pagination;
entries older than two minutes are ignored on restoration. Fresh requests always
run in the background. Storage failures are nonfatal. Live quotes, upcoming
forecasts, private account data and access policies are excluded.

Historical panels show the last load time and background refresh state. Existing
data remains visible if refresh fails, with a retry control.

Fallow was unavailable locally (`npx --no-install` reported a missing package).
No dependency was installed. Production deployment and browser verification are
not part of this change.
