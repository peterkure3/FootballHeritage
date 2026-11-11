import type { ReactNode } from "react";
import { FeatureLink as Link } from '../features/FeatureAccess';
import { sportPath, sports, type Sport } from "./data";
export function Footer() {
  return (
    <footer className="fh-footer">
      <div className="fh-footer-top">
        <div>
          <Link className="fh-footer-brand" to="/app">
            FootballHeritage<span>.</span>
          </Link>
          <p>The stories. The numbers. The game.</p>
        </div>
        <div>
          <h4>Explore</h4>
          {sports.slice(0, 4).map((sport) => (
            <Link key={sport} to={sportPath(sport)}>
              {sport}
            </Link>
          ))}
        </div>
        <div>
          <h4>Your game</h4>
          <Link to="/saved">Saved stories</Link>
          <Link to="/followed-teams">Followed teams</Link>
          <Link to="/profile">Profile</Link>
        </div>
        <div>
          <h4>Intelligence</h4>
          <Link to="/ai-picks">Best picks</Link>
          <Link to="/ai-picks/chat">Chat</Link>
          <Link to="/odds">Odds</Link>
          <Link to="/bets">Bet history</Link>
        </div>
      </div>
      <div className="fh-footer-bottom">
        <span>© {new Date().getFullYear()} FootballHeritage</span>
        <span>18+ · Play responsibly. Predictions are not guarantees.</span>
      </div>
    </footer>
  );
}
export default function AppShell({
  title,
  eyebrow = "THE STORIES. THE NUMBERS. THE GAME.",
  children,
}: {
  title: string;
  eyebrow?: string;
  sport?: Sport;
  children: ReactNode;
}) {
  return (
    <div className="fh-page">
      <div className="fh-intro">
        <div>
          <span className="fh-eyebrow">{eyebrow}</span>
          <h1>{title}</h1>
        </div>
        <span className="fh-intro-note">
          <i />
          Find your edge with data and insight.
        </span>
      </div>
      <div className="fh-layout">
        <main className="fh-content" id="main-content">
          {children}
        </main>
      </div>
      <Footer />
    </div>
  );
}
