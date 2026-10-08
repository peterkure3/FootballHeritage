import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Sparkles, Bookmark, Heart } from "lucide-react";
import { leagues, sportPath, sports, stories, type Sport } from "./data";
import { StoryImage } from "./ui";
import { usePreferences } from "./preferences";
export function LeftSidebar({ sport = "Football" }: { sport?: Sport }) {
  const follows = usePreferences("teams");
  return (
    <aside className="fh-left-sidebar">
      <div className="fh-card fh-your-game">
        <span className="fh-eyebrow">MADE FOR YOU</span>
        <h2>
          Your teams.
          <br />
          Your game.
        </h2>
        <p>Follow the teams you love. Keep the stories that matter.</p>
        <Link
          className="fh-button"
          to={follows.authenticated ? "/followed-teams" : "/register"}
        >
          {follows.authenticated ? "Your followed teams" : "Make it yours"}
          <ArrowUpRight size={14} />
        </Link>
      </div>
      <div className="fh-card fh-side-links">
        <h3>League shortcuts</h3>
        {Object.keys(leagues[sport]).map((league) => (
          <Link
            key={league}
            to={`${sportPath(sport, "schedule")}?competition=${encodeURIComponent(league)}`}
          >
            <span className="fh-team-badge">
              {league.slice(0, 2).toUpperCase()}
            </span>
            {league}
            <ArrowUpRight size={12} />
          </Link>
        ))}
      </div>
      <div className="fh-card fh-side-links">
        <h3>Your corner</h3>
        <Link to="/saved">
          <Bookmark size={15} />
          Saved stories
        </Link>
        <Link to="/followed-teams">
          <Heart size={15} />
          Followed teams
        </Link>
        {sports
          .filter((item) => item !== sport)
          .map((item) => (
            <Link key={item} to={sportPath(item)}>
              {item}
              <ArrowUpRight size={12} />
            </Link>
          ))}
      </div>
      <div className="fh-newsletter">
        <Sparkles size={23} />
        <h3>A smarter matchday.</h3>
        <p>
          Explore the numbers with FootballHeritage’s existing intelligence
          tools.
        </p>
        <Link to="/ai-picks">Explore AI Picks →</Link>
      </div>
    </aside>
  );
}
export function RightSidebar({ sport = "Football" }: { sport?: Sport }) {
  return (
    <aside className="fh-right-sidebar">
      <div className="fh-card fh-headlines">
        <div className="fh-panel-heading">
          <h3>The latest</h3>
          <span className="fh-demo">SAMPLE EDITORIAL</span>
        </div>
        {stories.map((story, index) => (
          <Link key={story.id} to={`/stories/${story.id}`}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div>
              <small>{story.tag}</small>
              <h4>{story.title}</h4>
            </div>
          </Link>
        ))}
      </div>
      <div className="fh-card fh-spotlight">
        <div className="fh-panel-heading">
          <h3>In the spotlight</h3>
          <span className="fh-demo">SAMPLE</span>
        </div>
        <Link to="/stories/african-game">
          <StoryImage src={stories[3].image} alt={stories[3].alt} />
          <div>
            <span className="fh-eyebrow">AFRICAN FOOTBALL</span>
            <h3>A game without borders.</h3>
          </div>
        </Link>
      </div>
      <div className="fh-card fh-mini-table">
        <div className="fh-panel-heading">
          <h3>Standings</h3>
        </div>
        <p>Standings data is not connected. No sample table is displayed.</p>
        <Link to={sportPath(sport, "standings")}>View availability →</Link>
      </div>
      <blockquote className="fh-quote">
        <span>“</span>The game is bigger than the result.
        <small>THE FOOTBALLHERITAGE WAY</small>
      </blockquote>
    </aside>
  );
}
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
  sport,
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
          Your daily sporting perspective
        </span>
      </div>
      <div className="fh-layout">
        <LeftSidebar sport={sport} />
        <main className="fh-content" id="main-content">
          {children}
        </main>
        <RightSidebar sport={sport} />
      </div>
      <Footer />
    </div>
  );
}
