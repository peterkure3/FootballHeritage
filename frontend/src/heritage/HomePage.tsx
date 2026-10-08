import { Link, useParams } from "react-router-dom";
import { Bookmark, ArrowUpRight, Sparkles } from "lucide-react";
import { useState } from "react";
import AppShell from "./AppShell";
import { stories, type Story, type Sport } from "./data";
import { StoryImage } from "./ui";
import { usePreferences } from "./preferences";
function SaveButton({ story }: { story: Story }) {
  const saved = usePreferences("stories");
  if (!saved.authenticated)
    return (
      <Link
        className="fh-save"
        to="/login"
        aria-label={`Log in to save ${story.title}`}
      >
        <Bookmark size={17} />
      </Link>
    );
  return (
    <button
      className="fh-save"
      aria-pressed={saved.values.includes(story.id)}
      aria-label={`${saved.values.includes(story.id) ? "Unsave" : "Save"} ${story.title}`}
      onClick={() => saved.toggle(story.id)}
    >
      <Bookmark
        size={17}
        fill={saved.values.includes(story.id) ? "currentColor" : "none"}
      />
    </button>
  );
}
export function StoryCard({
  story,
  hero = false,
}: {
  story: Story;
  hero?: boolean;
}) {
  return (
    <article className={hero ? "fh-hero" : "fh-story-card"}>
      <Link className="fh-story-image" to={`/stories/${story.id}`}>
        <StoryImage src={story.image} alt={story.alt} />
      </Link>
      <div className="fh-story-body">
        <span className="fh-eyebrow">{story.tag}</span>
        <span className="fh-demo">SAMPLE EDITORIAL</span>
        <Link to={`/stories/${story.id}`}>
          <h2>{story.title}</h2>
        </Link>
        <p>{story.description}</p>
        <div className="fh-story-meta">
          <span>FootballHeritage · Template preview</span>
          <SaveButton story={story} />
        </div>
      </div>
    </article>
  );
}
export default function HomePage({
  sport,
  savedOnly = false,
}: {
  sport?: Sport;
  savedOnly?: boolean;
}) {
  const [tab, setTab] = useState("For you");
  const saved = usePreferences("stories");
  const selected = stories.filter(
    (story) =>
      (!sport || story.sport === sport) &&
      (!savedOnly || saved.values.includes(story.id)),
  );
  return (
    <AppShell
      sport={sport}
      title={
        savedOnly
          ? "Your saved stories."
          : sport
            ? `${sport}. Beyond the score.`
            : "A world of sport. A deeper perspective."
      }
    >
      {!savedOnly && (
        <div className="fh-tabs" aria-label="Story feed">
          <button
            className={tab === "For you" ? "selected" : ""}
            onClick={() => setTab("For you")}
          >
            For you
          </button>
          <Link to="/followed-teams">Following</Link>
          <Link to="/saved">Saved</Link>
          <span>Editorial preview</span>
        </div>
      )}
      <p className="fh-data-note">
        Template sample editorial — not live reporting. A newsroom API is not
        available.
      </p>
      {savedOnly && (
        <p className="fh-data-note">
          Saved for your account on this device only. Server sync is not
          available.
        </p>
      )}
      {selected.length ? (
        <>
          {selected.map((story, index) => (
            <StoryCard key={story.id} story={story} hero={index === 0} />
          ))}
          <div className="fh-insight-banner">
            <Sparkles size={30} />
            <div>
              <span className="fh-eyebrow">BEYOND THE SCORE</span>
              <h3>Let the numbers tell their story.</h3>
              <p>Explore existing predictions and intelligence tools.</p>
            </div>
            <Link to="/ai-picks" aria-label="Explore AI Picks">
              <ArrowUpRight />
            </Link>
          </div>
        </>
      ) : (
        <div className="fh-card fh-state">
          <h2>
            {savedOnly
              ? "No saved stories yet."
              : "Stories not available for this sport."}
          </h2>
          <p>
            {savedOnly && !saved.authenticated
              ? "Log in to save stories to your account on this device."
              : "We will not substitute unrelated stories as live coverage."}
          </p>
          <Link className="fh-button" to={saved.authenticated ? "/" : "/login"}>
            {saved.authenticated ? "Explore stories" : "Log in"}
          </Link>
        </div>
      )}
    </AppShell>
  );
}
export function StoryPage() {
  const { id } = useParams();
  const story = stories.find((item) => item.id === id);
  return (
    <AppShell title={story?.title || "Story not found."} sport={story?.sport}>
      {story ? (
        <article className="fh-card fh-article">
          <StoryImage src={story.image} alt={story.alt} />
          <div>
            <span className="fh-demo">SAMPLE EDITORIAL FROM THE TEMPLATE</span>
            <h2>{story.title}</h2>
            <p>{story.description}</p>
            <p>
              This is a design preview, not a published news report. No
              editorial article service is connected.
            </p>
            <SaveButton story={story} />
          </div>
        </article>
      ) : (
        <Link to="/">Return to homepage</Link>
      )}
    </AppShell>
  );
}
