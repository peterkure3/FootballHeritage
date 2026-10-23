import { createElement, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  Wallet,
  Ticket,
  Target,
  Clock3,
  ShieldCheck,
  Sparkles,
  BarChart3,
  Bookmark,
  RefreshCw,
} from "lucide-react";
import { useUser } from "../hooks/useAuth";
import { useBetsHistory } from "../hooks/useBetting";
import useBettingStore from "../stores/bettingStore";
import "./Dashboard.css";

const money = (value) =>
  ![null, undefined, ""].includes(value) && Number.isFinite(Number(value))
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
      }).format(Number(value))
    : "—";
const statusOf = (bet) => (bet.status || "unknown").toLowerCase();
const isOpen = (bet) => ["pending", "active"].includes(statusOf(bet));
const isWon = (bet) => ["won", "settled_won"].includes(statusOf(bet));
const isLost = (bet) => ["lost", "settled_lost"].includes(statusOf(bet));
const dateOf = (bet) =>
  bet.placed_at || bet.placedAt || bet.timestamp || bet.created_at;
const timestamp = (bet) => new Date(dateOf(bet)).getTime() || 0;
const dateLabel = (bet) =>
  timestamp(bet)
    ? new Date(dateOf(bet)).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    : "Date unavailable";
const shortcuts = [
  {
    title: "AI picks",
    detail: "Explore model insights",
    to: "/ai-picks",
    icon: Sparkles,
  },
  {
    title: "Predictions",
    detail: "Look closer at the numbers",
    to: "/predictions",
    icon: BarChart3,
  },
  {
    title: "Saved picks",
    detail: "Return to your shortlist",
    to: "/saved",
    icon: Bookmark,
  },
];

function Metric({ label, value, detail, icon: Icon }) {
  return (
    <article className="ud-metric">
      <div>
        <span>{label}</span>
        {createElement(Icon, { size: 18, "aria-hidden": true })}
      </div>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

function BetRow({ bet }) {
  const outcome = isWon(bet)
    ? "won"
    : isLost(bet)
      ? "lost"
      : isOpen(bet)
        ? "pending"
        : "other";
  const label =
    { won: "Won", lost: "Lost", pending: "Pending" }[outcome] ||
    statusOf(bet).replaceAll("_", " ");
  const selection =
    bet.selection ||
    (bet.type || bet.bet_type || "Selection unavailable").replaceAll("_", " ");
  return (
    <article className="ud-bet-row">
      <div className={`ud-bet-icon ud-${outcome}`}>
        <Ticket size={19} aria-hidden="true" />
      </div>
      <div className="ud-bet-event">
        <h3>
          {bet.event_name ||
            bet.eventName ||
            `Event #${bet.event_id || bet.eventId || "unavailable"}`}
        </h3>
        <p>
          {selection} · {dateLabel(bet)}
        </p>
      </div>
      <div className="ud-bet-amount">
        <strong>{money(bet.amount)}</strong>
        <span>Stake · {bet.odds || "—"} odds</span>
      </div>
      <span className={`ud-status ud-${outcome}`}>{label}</span>
    </article>
  );
}

function Activity({ query, bets }) {
  const [filter, setFilter] = useState("All bets");
  const filtered = bets.filter(
    (bet) =>
      filter === "All bets" ||
      (filter === "Pending" ? isOpen(bet) : isWon(bet) || isLost(bet)),
  );
  return (
    <section className="ud-panel ud-activity" aria-labelledby="activity-title">
      <div className="ud-panel-heading">
        <div>
          <span className="ud-eyebrow">YOUR BETTING JOURNAL</span>
          <h2 id="activity-title">Recent activity</h2>
        </div>
        <Link to="/bets">
          Full history <ArrowUpRight size={16} aria-hidden="true" />
        </Link>
      </div>
      <div
        className="ud-filters"
        role="group"
        aria-label="Filter betting activity"
      >
        {["All bets", "Pending", "Settled"].map((label) => (
          <button
            type="button"
            key={label}
            aria-pressed={filter === label}
            onClick={() => setFilter(label)}
          >
            {label}
          </button>
        ))}
      </div>
      {query.isError && (
        <div className="ud-error" role="alert">
          <p>
            Bet history could not be refreshed.{" "}
            {query.data
              ? "Showing the last available activity."
              : "Your activity is unavailable."}
          </p>
          <button
            type="button"
            disabled={query.isFetching}
            onClick={() => query.refetch()}
          >
            Retry bet history
          </button>
        </div>
      )}
      {query.isLoading ? (
        <div className="ud-loading" role="status">
          Loading your betting activity…
          <div />
          <div />
          <div />
        </div>
      ) : filtered.length ? (
        <div>
          {filtered.slice(0, 5).map((bet) => (
            <BetRow key={bet.id || bet.bet_id} bet={bet} />
          ))}
        </div>
      ) : (
        !query.isError && (
          <div className="ud-empty">
            <Ticket size={30} aria-hidden="true" />
            <h3>
              {filter === "All bets"
                ? "Your story starts here"
                : `No ${filter.toLowerCase()} bets`}
            </h3>
            <p>
              {filter === "All bets"
                ? "Your betting activity will appear here when you place a bet."
                : "Bets with this status will appear here."}
            </p>
            <Link to="/odds">
              Explore the markets <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
        )
      )}
      <div className="ud-activity-note">
        <Clock3 size={14} aria-hidden="true" /> Latest five shown. Activity
        refreshes every 30 seconds.
      </div>
    </section>
  );
}

function SessionCard() {
  const total = useBettingStore((state) => state.sessionTotal);
  const limit = useBettingStore((state) => state.sessionLimit);
  const percentage = Math.min(
    100,
    Math.max(0, Math.round((total / limit) * 100)),
  );
  return (
    <section
      className={`ud-panel ud-session ${percentage >= 80 ? "ud-session-warning" : ""}`}
      aria-labelledby="session-title"
    >
      <div className="ud-session-icon">
        <ShieldCheck size={22} aria-hidden="true" />
      </div>
      <span className="ud-eyebrow">STAY IN CONTROL</span>
      <h2 id="session-title">Play at your pace.</h2>
      <p>A clear limit helps keep the game enjoyable.</p>
      <div className="ud-session-totals">
        <strong>
          {money(total)} <small>/ {money(limit)}</small>
        </strong>
        <span>{percentage}% used</span>
      </div>
      <progress
        value={percentage}
        max="100"
        aria-label="Session stake limit used"
      />
      <p className="ud-session-caption">
        {money(Math.max(0, limit - total))} remaining in this browser session.
      </p>
      <div className="ud-session-message">
        {percentage >= 80
          ? "You’re approaching your session limit. Take a break before placing another bet."
          : "Only stake what you can afford to lose. Taking a break is always a good call."}
      </div>
    </section>
  );
}

export default function Dashboard() {
  const userQuery = useUser();
  const betsQuery = useBetsHistory();
  const user = userQuery.data;
  const bets = Array.isArray(betsQuery.data)
    ? [...betsQuery.data].sort((a, b) => timestamp(b) - timestamp(a))
    : [];
  const won = bets.filter(isWon).length;
  const lost = bets.filter(isLost).length;
  const pending = bets.filter(isOpen).length;
  const ready = betsQuery.data !== undefined;
  const metric = (value) => (ready ? value : "—");
  const name = user?.first_name || user?.email?.split("@")[0];
  const busy = userQuery.isFetching || betsQuery.isFetching;
  return (
    <main className="user-dashboard">
      <div className="ud-breadcrumb">
        <Link to="/app">Home</Link>
        <span>/</span>
        <span>My dashboard</span>
      </div>
      <header className="ud-header">
        <div>
          <span className="ud-eyebrow">YOUR PERSONAL CLUBHOUSE</span>
          <h1>Welcome back{name ? `, ${name}` : ""}.</h1>
          <p>Your activity, your insights, your game plan.</p>
        </div>
        <button
          className="ud-refresh"
          type="button"
          disabled={busy}
          onClick={() => {
            userQuery.refetch();
            betsQuery.refetch();
          }}
        >
          <RefreshCw size={15} aria-hidden="true" />
          {busy ? "Refreshing…" : "Refresh overview"}
        </button>
      </header>
      <div className="ud-overview">
        <section className="ud-wallet" aria-labelledby="balance-title">
          <div className="ud-wallet-top">
            <span id="balance-title">AVAILABLE BALANCE</span>
            <Wallet size={21} aria-hidden="true" />
          </div>
          <strong>
            {userQuery.isLoading ? "Loading…" : money(user?.balance)}
          </strong>
          <p>
            {userQuery.isError
              ? "Balance could not be refreshed."
              : "Your account, at a glance."}
          </p>
          <Link to="/profile">
            Manage account <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
          <span className="ud-wallet-decoration" aria-hidden="true">
            FH
          </span>
        </section>
        <div className="ud-metrics">
          <Metric
            label="Total bets"
            value={metric(bets.length)}
            detail="Across your betting history"
            icon={Ticket}
          />
          <Metric
            label="Win rate"
            value={metric(
              won + lost ? `${Math.round((won / (won + lost)) * 100)}%` : "—",
            )}
            detail={
              ready
                ? `${won} won · ${lost} lost · settled only`
                : "Awaiting betting history"
            }
            icon={Target}
          />
          <Metric
            label="Open bets"
            value={metric(pending)}
            detail="Awaiting a result"
            icon={Clock3}
          />
        </div>
      </div>
      {userQuery.isError && (
        <div className="ud-error" role="alert">
          <p>Your account details could not be refreshed.</p>
          <button
            type="button"
            disabled={userQuery.isFetching}
            onClick={() => userQuery.refetch()}
          >
            Retry account
          </button>
        </div>
      )}
      <div className="ud-main-grid">
        <div className="ud-main-column">
          <div className="ud-section-label">
            <h2>A little insight. A better game plan.</h2>
            <span>EXPLORE FOOTBALLHERITAGE</span>
          </div>
          <nav className="ud-shortcuts" aria-label="Dashboard shortcuts">
            {shortcuts.map(({ title, detail, to, icon: Icon }) => (
              <Link key={to} to={to}>
                {createElement(Icon, { size: 22, "aria-hidden": true })}
                <h3>{title}</h3>
                <p>{detail}</p>
                <ArrowUpRight
                  className="ud-shortcut-arrow"
                  size={17}
                  aria-hidden="true"
                />
              </Link>
            ))}
          </nav>
          <Activity query={betsQuery} bets={bets} />
        </div>
        <aside className="ud-aside">
          <SessionCard />
          <section className="ud-explore">
            <span className="ud-eyebrow">THE NEXT CHAPTER</span>
            <h2>
              Follow the game
              <br />
              beyond the score.
            </h2>
            <p>Fixtures, markets, and match insights. All in one place.</p>
            <Link to="/odds">
              Explore odds <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </section>
        </aside>
      </div>
      <footer className="ud-footer">
        <span>
          <ShieldCheck size={15} aria-hidden="true" /> Play responsibly. Stay in
          control.
        </span>
        <span>18+ · Every outcome carries risk.</span>
      </footer>
    </main>
  );
}
