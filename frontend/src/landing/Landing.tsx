import { useState, type MouseEvent } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  Sparkles,
  BarChart3,
  Globe2,
} from "lucide-react";
import LandingNavbar from "./LandingNavbar";
import { sports } from "../heritage/data";
import "./landing.css";

const features = [
  {
    Icon: Globe2,
    title: "Your matchday, in one place.",
    body: "Browse available scores and fixtures, explore the sports directory, and keep your favorite teams close.",
  },
  {
    Icon: BarChart3,
    title: "Go beyond the scoreboard.",
    body: "Explore available football predictions and odds analysis, with data availability and limitations made clear.",
  },
  {
    Icon: Sparkles,
    title: "Meet AI Picks.",
    body: "Inspect selections from the football model service. Use Chat to ask questions, while distinguishing provider explanations from predictions.",
  },
];

function resetLandingScroll(event: MouseEvent<HTMLDivElement>) {
  if (
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  )
    return;
  if (event.target instanceof Element && event.target.closest('a[href^="/"]')) {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }
}

function StadiumHero() {
  const [unavailable, setUnavailable] = useState(false);
  return (
    <div className="landing-photo">
      {unavailable ? (
        <div
          className="landing-photo-fallback"
          role="img"
          aria-label="Stadium image unavailable"
        >
          <span>Stadium image unavailable</span>
        </div>
      ) : (
        <img
          src="/images/stadium.jpg"
          alt="Football stadium illuminated under the night sky"
          fetchPriority="high"
          decoding="async"
          onError={() => setUnavailable(true)}
        />
      )}
      <span className="landing-photo-label">THE MATCHDAY FEELING</span>
      <div className="landing-photo-caption">
        <span>EVERY MATCH HAS A STORY.</span>
        <h2>
          There’s more to the game
          <br />
          than the final score.
        </h2>
      </div>
      <div className="landing-photo-number">01 / FOOTBALLHERITAGE</div>
    </div>
  );
}

function PlatformFeatures() {
  return (
    <section
      className="landing-features"
      aria-labelledby="landing-features-title"
    >
      <div className="landing-section-heading">
        <span className="landing-kicker">A DIFFERENT VIEW OF SPORT</span>
        <h2 id="landing-features-title">
          From the touchline
          <br />
          to the bigger picture.
        </h2>
        <p>
          Keep the atmosphere. Add the context. Make FootballHeritage your
          starting point for every matchday.
        </p>
        <p className="landing-availability">
          Coverage depends on available data. Standings and newsroom feeds are
          not connected; editorial previews are labeled samples. Team follows
          are saved on your device.
        </p>
      </div>
      <div className="landing-feature-list">
        {features.map(({ Icon, title, body }, index) => (
          <article key={title}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div>
              <Icon size={22} aria-hidden="true" />
              <h3>{title}</h3>
              <p>{body}</p>
            </div>
            <ArrowUpRight size={20} aria-hidden="true" />
          </article>
        ))}
      </div>
    </section>
  );
}

function AiIntroduction() {
  return (
    <section className="landing-ai" aria-labelledby="landing-ai-title">
      <div>
        <span className="landing-kicker">
          <Sparkles size={14} aria-hidden="true" /> INTELLIGENCE WITH CONTEXT
        </span>
        <h2 id="landing-ai-title">
          Ask better questions.
          <br />
          See the game differently.
        </h2>
        <p>
          Best picks displays selections from the connected football model
          service. Chat offers provider-generated explanations, not model
          predictions. Missing evidence and fields are shown as unavailable.
        </p>
        <small>
          AI features require connected model and chat services. Generation
          currently supports Football only. Predictions are estimates, not
          guarantees.
        </small>
      </div>
      <div className="landing-ai-demo">
        <span>AI PICKS / A LOOK INSIDE</span>
        <div>
          <Sparkles size={19} aria-hidden="true" />
          <h3>What’s behind a pick?</h3>
        </div>
        <ul>
          <li>Selections, markets and available odds</li>
          <li>Model probabilities and available timestamps</li>
          <li>Data gaps, explanations and limitations</li>
        </ul>
        <Link to="/app">
          Explore the platform <ArrowUpRight size={17} aria-hidden="true" />
        </Link>
      </div>
    </section>
  );
}

export default function Landing() {
  return (
    <div className="fh-landing" onClickCapture={resetLandingScroll}>
      <a className="landing-skip" href="#landing-content">
        Skip to content
      </a>
      <LandingNavbar />
      <main id="landing-content" tabIndex={-1}>
        <section className="landing-hero" aria-labelledby="landing-hero-title">
          <div className="landing-hero-copy">
            <span className="landing-kicker">
              <span className="landing-green-dot" /> FOR THE LOVE OF THE GAME
            </span>
            <h1 id="landing-hero-title">
              Feel the game.
              <br />
              Read the numbers.
              <br />
              <em>Find your edge.</em>
            </h1>
            <p>
              FootballHeritage brings available fixtures and sports intelligence
              into one place. Follow your teams. Explore the matchday. Go deeper
              with AI Picks.
            </p>
            <div className="landing-cta">
              <Link to="/register">
                Create your account{" "}
                <ArrowUpRight size={19} aria-hidden="true" />
              </Link>
              <Link to="/app">
                Explore FootballHeritage{" "}
                <ArrowRight size={17} aria-hidden="true" />
              </Link>
            </div>
            <small>Built for fans. Driven by curiosity.</small>
          </div>
          <StadiumHero />
        </section>
        <div className="landing-sports" aria-label="Sports directory">
          <span>ONE HOME. EVERY GAME.</span>
          {sports.map((sport) => (
            <span key={sport}>{sport}</span>
          ))}
        </div>
        <PlatformFeatures />
        <AiIntroduction />
        <section
          className="landing-final"
          aria-labelledby="landing-final-title"
        >
          <span className="landing-kicker">YOUR NEXT MATCHDAY STARTS HERE</span>
          <h2 id="landing-final-title">
            The game is better
            <br />
            when you see more of it.
          </h2>
          <Link to="/register">
            Join FootballHeritage <ArrowUpRight size={18} aria-hidden="true" />
          </Link>
        </section>
      </main>
      <footer className="landing-footer">
        <Link
          to="/"
          className="landing-footer-brand"
          aria-label="FootballHeritage home"
        >
          footballheritage<span>.</span>
        </Link>
        <span>
          © {new Date().getFullYear()} FootballHeritage · 21+ · Play
          responsibly.
        </span>
        <div>
          <Link to="/register">Register</Link>
          <Link to="/login">Login</Link>
        </div>
      </footer>
    </div>
  );
}
