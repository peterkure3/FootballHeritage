const exactFeatures = {
  '/register': 'registration', '/ai-picks/chat': 'ai_chat', '/chat': 'ai_chat',
  '/smart-assistant': 'ai_chat', '/best-bets': 'best_picks', '/predictions': 'predictions',
  '/player-props': 'player_props', '/parlay-calculator': 'parlays', '/odds': 'betting',
  '/bets': 'betting', '/fpl-advisor': 'fpl', '/sports': 'sports',
};
const prefixes = [
  ['/ai-picks/intelligence', 'intelligence'], ['/intelligence/', 'intelligence'],
  ['/ai-picks', 'ai_picks'], ['/college', 'college'], ['/sport/', 'sports'],
];
export function featureForPath(path) {
  const p = path.split('?')[0];
  return exactFeatures[p] ?? prefixes.find(([prefix]) => p.startsWith(prefix))?.[1] ?? null;
}

export function hasFeature(data, key) {
  return data?.features?.[key] === true;
}
