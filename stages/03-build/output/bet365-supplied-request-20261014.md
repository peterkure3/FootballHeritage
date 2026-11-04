# Bet365 supplied request — 2026-10-14

The supplied GET to
`https://www.bet365.com/gamingservices/gam-client-games-svcv1/api/getallgamesv2`
returned HTTP 200 application/json without browser cookies. Its root is `games`;
records contain casino game titles, images, game identifiers and lobby labels,
including Gold Wired, Fat Cats DoubleMax and Big Bass Halloween Splash 1000.
This response is a casino catalog and cannot supply football fixtures or 1X2 odds.

Evidence: `pipeline/data/raw/sportsbooks/supplied_bet365_20261014T041433863610Z/`
contains the anonymous response and HTTP metadata report. No user session cookies
were persisted, no odds were imported, and the 45-source catalog is unchanged.

A sports request captured while opening Football → UEFA Champions League is
needed. Inspect its Response/Preview for team names, fixture times and 1/X/2
prices before copying the request. The response need not be JSON; text feeds or
WebSocket frames should be identified as such.
