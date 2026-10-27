"""Shared football competition identities for collection and grid ingestion."""

# Keep football-data.org names as database keys; use familiar names in the UI.
LEAGUES = [
    ('PL', 'Premier League', 'England', 'soccer_epl'),
    ('CL', 'UEFA Champions League', 'International', 'soccer_uefa_champs_league'),
    ('PD', 'Primera Division', 'Spain', 'soccer_spain_la_liga'),
    ('BL1', 'Bundesliga', 'Germany', 'soccer_germany_bundesliga'),
    ('SA', 'Serie A', 'Italy', 'soccer_italy_serie_a'),
    ('FL1', 'Ligue 1', 'France', 'soccer_france_ligue_one'),
    ('PPL', 'Primeira Liga', 'Portugal', 'soccer_portugal_primeira_liga'),
    ('DED', 'Eredivisie', 'Netherlands', 'soccer_netherlands_eredivisie'),
    ('ELC', 'Championship', 'England', 'soccer_efl_champ'),
    ('BSA', 'Campeonato Brasileiro S\u00e9rie A', 'Brazil', 'soccer_brazil_campeonato'),
]
DISPLAY_NAMES = {'Primera Division': 'La Liga'}
PUBLIC_LEAGUES = {(country, name) for _, name, country, _ in LEAGUES}
PUBLIC_LEAGUES.add(('Spain', 'La Liga'))
PUBLIC_LEAGUES.update({('Spain', 'LaLiga'), ('Portugal', 'Liga Portugal'),
                      ('Brazil', 'Brasileiro Serie A')})
COMPETITION_ALIASES = {}
for code, name, country, sport in LEAGUES:
    for alias in (code, name, sport, f'{country} {name}', f'{country} - {name}'):
        COMPETITION_ALIASES[alias] = name
COMPETITION_ALIASES.update({
    'La Liga': 'Primera Division', 'LaLiga': 'Primera Division',
    '1. Bundesliga': 'Bundesliga',
    'Spain La Liga': 'Primera Division', 'Spain - La Liga': 'Primera Division',
    'UEFA - Champions League': 'UEFA Champions League',
    'Europe - UEFA Champions League': 'UEFA Champions League',
    'Liga Portugal': 'Primeira Liga', 'Brasileir\u00e3o S\u00e9rie A': 'Campeonato Brasileiro S\u00e9rie A',
    'Brasileiro Serie A': 'Campeonato Brasileiro S\u00e9rie A',
})


def canonical_competition(name: str, country: str | None = None) -> str | None:
    """Reject unrelated leagues sharing a name in another country."""
    canonical = COMPETITION_ALIASES.get(name)
    if canonical is None:
        return None
    expected = next(row[2] for row in LEAGUES if row[1] == canonical)
    allowed = {expected}
    if canonical == 'UEFA Champions League':
        allowed.update({'Europe', 'UEFA', 'International Clubs'})
    if country and country not in allowed:
        return None
    return canonical
