-- Local only; requires the existing matches, predictions and odds tables.
-- Capture source changes in the producer's own transaction, without Python hooks.
CREATE TABLE fh_sync.dirty_fixtures (
    match_id INTEGER PRIMARY KEY,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    blocked_at TIMESTAMPTZ,
    error_code TEXT
);
CREATE FUNCTION fh_sync.mark_fixture_dirty() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    previous_id INTEGER;
    current_id INTEGER;
BEGIN
    IF TG_OP <> 'INSERT' THEN previous_id := OLD.match_id; END IF;
    IF TG_OP <> 'DELETE' THEN current_id := NEW.match_id; END IF;
    INSERT INTO fh_sync.dirty_fixtures(match_id)
    SELECT DISTINCT id FROM unnest(ARRAY[previous_id,current_id]) AS id WHERE id IS NOT NULL
    ON CONFLICT(match_id) DO UPDATE SET changed_at=clock_timestamp(),blocked_at=NULL,error_code=NULL;
    RETURN NULL;
END;
$$;
CREATE TRIGGER fh_sync_matches AFTER INSERT OR UPDATE OR DELETE ON public.matches
    FOR EACH ROW EXECUTE FUNCTION fh_sync.mark_fixture_dirty();
CREATE TRIGGER fh_sync_predictions AFTER INSERT OR UPDATE OR DELETE ON public.predictions
    FOR EACH ROW EXECUTE FUNCTION fh_sync.mark_fixture_dirty();
CREATE TRIGGER fh_sync_odds AFTER INSERT OR UPDATE OR DELETE ON public.odds
    FOR EACH ROW EXECUTE FUNCTION fh_sync.mark_fixture_dirty();
REVOKE ALL ON FUNCTION fh_sync.mark_fixture_dirty() FROM PUBLIC;
