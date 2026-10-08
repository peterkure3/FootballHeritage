export const sports = [
  "Football",
  "NBA",
  "NFL",
  "WNBA",
  "NCAAB",
  "College Football",
] as const;
export type Sport = (typeof sports)[number];
export const slug = (sport: string) => sport.toLowerCase().replaceAll(" ", "-");
export const sportPath = (sport: string, section = "home") =>
  `/sport/${slug(sport)}${section === "home" ? "" : `/${section}`}`;
export const sections = [
  "Home",
  "Scores",
  "Schedule",
  "Standings",
  "Teams",
  "Insights",
];
// Navigation directory from the supplied template, not a claim of data/model coverage.
export const leagues: Record<Sport, Record<string, string[]>> = {
  Football: {
    "Premier League": [
      "Arsenal",
      "Chelsea",
      "Liverpool",
      "Manchester City",
      "Manchester United",
      "Tottenham",
    ],
    "La Liga": [
      "Real Madrid",
      "Barcelona",
      "Atlético Madrid",
      "Athletic Club",
      "Real Sociedad",
      "Villarreal",
    ],
    Bundesliga: [
      "Bayern Munich",
      "Borussia Dortmund",
      "Bayer Leverkusen",
      "RB Leipzig",
      "Eintracht Frankfurt",
      "Stuttgart",
    ],
    "European & international": [
      "Champions League",
      "Europa League",
      "Serie A",
      "Ligue 1",
      "AFCON",
      "Uganda Premier League",
    ],
  },
  NBA: {
    "Eastern Conference": [
      "Boston Celtics",
      "New York Knicks",
      "Cleveland Cavaliers",
      "Milwaukee Bucks",
      "Miami Heat",
      "Orlando Magic",
    ],
    "Western Conference": [
      "Los Angeles Lakers",
      "Golden State Warriors",
      "Denver Nuggets",
      "Oklahoma City Thunder",
      "Dallas Mavericks",
      "Houston Rockets",
    ],
  },
  NFL: {
    "AFC East": [
      "Buffalo Bills",
      "Miami Dolphins",
      "New England Patriots",
      "New York Jets",
    ],
    "AFC North": [
      "Baltimore Ravens",
      "Cincinnati Bengals",
      "Cleveland Browns",
      "Pittsburgh Steelers",
    ],
    "AFC West & South": [
      "Kansas City Chiefs",
      "Denver Broncos",
      "Houston Texans",
      "Indianapolis Colts",
    ],
    NFC: [
      "Dallas Cowboys",
      "Philadelphia Eagles",
      "San Francisco 49ers",
      "Detroit Lions",
      "Green Bay Packers",
      "Seattle Seahawks",
    ],
  },
  WNBA: {
    Teams: [
      "Las Vegas Aces",
      "New York Liberty",
      "Indiana Fever",
      "Seattle Storm",
      "Minnesota Lynx",
      "Atlanta Dream",
      "Phoenix Mercury",
      "Chicago Sky",
    ],
  },
  NCAAB: {
    Conferences: [
      "ACC",
      "Big Ten",
      "Big 12",
      "SEC",
      "Big East",
      "Mountain West",
    ],
    Explore: [
      "Men’s basketball",
      "Women’s basketball",
      "Rankings",
      "March Madness",
    ],
  },
  "College Football": {
    Conferences: [
      "SEC",
      "Big Ten",
      "ACC",
      "Big 12",
      "American",
      "Mountain West",
    ],
    Explore: [
      "Rankings",
      "College Football Playoff",
      "Recruiting",
      "Bowl games",
    ],
  },
};
export interface Story {
  id: string;
  tag: string;
  title: string;
  description: string;
  image: string;
  alt: string;
  sport: Sport;
}
// Explicit sample editorial content: this repository has no newsroom API.
export const stories: Story[] = [
  {
    id: "lights",
    tag: "THE BIG PICTURE",
    title: "Under the lights. Beyond the ordinary.",
    description:
      "The nights that remind us why we fell in love with football. Inside a new chapter of European competition.",
    image: "/images/stadium.jpg",
    alt: "A football stadium illuminated under the evening sky",
    sport: "Football",
  },
  {
    id: "north-london",
    tag: "PREMIER LEAGUE",
    title: "A new generation. The same North London ambition.",
    description:
      "Youth, belief and the fine margins that shape a title challenge.",
    image: "/images/football.jpg",
    alt: "Football on a green playing field",
    sport: "Football",
  },
  {
    id: "hardwood",
    tag: "NBA",
    title: "The next chapter starts on the hardwood.",
    description:
      "Five storylines to follow as basketball returns to the spotlight.",
    image: "/images/basketball.jpg",
    alt: "Basketball court and hoop",
    sport: "NBA",
  },
  {
    id: "african-game",
    tag: "AFRICAN FOOTBALL",
    title: "From the local pitch to the continental stage.",
    description:
      "Meet the communities building the future of the African game.",
    image: "/images/pitch.jpg",
    alt: "Players on a football pitch",
    sport: "Football",
  },
  {
    id: "every-yard",
    tag: "NFL",
    title: "Every yard matters: the battles that define a season.",
    description:
      "Inside the tactics, matchups and preparation behind Sunday’s biggest games.",
    image: "/images/nfl.jpg",
    alt: "American football players at a stadium",
    sport: "NFL",
  },
];
