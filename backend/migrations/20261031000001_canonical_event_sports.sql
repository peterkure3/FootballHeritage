-- Classify legacy football using league evidence before resolving aliases.
CREATE OR REPLACE FUNCTION canonical_event_sport(raw_sport text, league text)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE
        WHEN lower(trim(raw_sport)) IN ('football','soccer','nfl','ncaaf','americanfootball','american football')
             AND (lower(trim(raw_sport)) IN ('nfl','ncaaf','americanfootball','american football')
                  OR lower(coalesce(league,'')) ~ '(^|[^a-z])(nfl|ncaaf|ncaa football|college football|american football)([^a-z]|$)'
                  OR lower(coalesce(league,'')) LIKE 'americanfootball%') THEN 'NFL'
        WHEN lower(trim(raw_sport)) IN ('football','soccer') THEN 'SOCCER'
        WHEN lower(trim(raw_sport)) IN ('basketball','nba','wnba','nba_cup','ncaab','ncaabw') THEN 'BASKETBALL'
        ELSE upper(trim(raw_sport))
    END
$$;

CREATE OR REPLACE FUNCTION normalize_event_sport() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.sport := canonical_event_sport(NEW.sport, NEW.league);
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS events_normalize_sport ON events;
CREATE TRIGGER events_normalize_sport BEFORE INSERT OR UPDATE OF sport, league ON events
FOR EACH ROW EXECUTE FUNCTION normalize_event_sport();

UPDATE events SET sport = canonical_event_sport(sport, league)
WHERE sport IS DISTINCT FROM canonical_event_sport(sport, league);
