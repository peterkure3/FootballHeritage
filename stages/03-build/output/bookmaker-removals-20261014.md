# Bookmaker removals — 2026-10-14

Removed at the user's request: AbaBet (interpreting "adabet"), AdmiralBet,
BetMGM, BetLion, BetKing, Bally Bet, Bangbet, Bet.co.za ZA, Bet9ja NG and BetRivers.
The canonical inventory now has 45 bookmakers. AbaBet was also removed from
the regional refresh targets; the other nine were not regional refresh targets.

The grid uses the supplied catalog as its column list, so retained historical
quotes cannot restore a removed source. Quote-derived columns remain a fallback
for responses that do not supply a catalog. Historical odds records are retained.

Verified: two Python catalog/matching checks and live API response with 45 catalog
entries and none of the ten removed source IDs. Browser regression includes an
AbaBet historical quote absent from the catalog and checks it stays hidden.
All four focused Chromium checks passed (the catalog regression passed on rerun
after completing its mock quote); targeted ESLint passed.
