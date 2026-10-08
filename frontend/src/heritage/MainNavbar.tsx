import {
  useState,
  useRef,
  useEffect,
  useLayoutEffect,
  type ReactNode,
  type Dispatch,
  type SetStateAction,
} from "react";
import { Link, useLocation } from "react-router-dom";
import {
  ChevronDown,
  Menu,
  X,
  Sparkles,
  UserRound,
  ArrowUpRight,
  Activity,
} from "lucide-react";
import useAuthStore from "../stores/authStore";
import WalletModal from "../components/WalletModal";
import Brand from "./Brand";
import { sports, leagues, sportPath, sections, slug, type Sport } from "./data";
import { useFixtures, formatDate } from "./services";

function MenuGroup({
  name,
  label,
  open,
  setOpen,
  children,
  destination,
  className = "",
}: {
  name: string;
  label: ReactNode;
  open: string;
  setOpen: Dispatch<SetStateAction<string>>;
  children: ReactNode;
  destination?: string;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  const show = () => {
    clearTimeout(closeTimer.current);
    setOpen(name);
  };
  useEffect(() => () => clearTimeout(closeTimer.current), []);
  return (
    <div
      ref={ref}
      className={`fh-menu-group ${className}`}
      onMouseEnter={show}
      onMouseMove={() => {
        if (!destination) show();
      }}
      onMouseLeave={() => {
        clearTimeout(closeTimer.current);
        closeTimer.current = setTimeout(() => {
          if (!ref.current?.contains(document.activeElement))
            setOpen((current) => (current === name ? "" : current));
        }, 180);
      }}
      onFocus={show}
      onBlur={(event) => {
        if (
          event.relatedTarget &&
          !event.currentTarget.contains(event.relatedTarget)
        )
          setOpen((current) => (current === name ? "" : current));
      }}
    >
      {destination ? (
        <Link
          className="fh-menu-trigger"
          to={destination}
          aria-expanded={open === name}
          aria-controls={`menu-${name}`}
        >
          {label}
          <ChevronDown size={12} />
        </Link>
      ) : (
        <button
          aria-expanded={open === name}
          aria-controls={`menu-${name}`}
          onClick={() => setOpen(name)}
        >
          {label}
          <ChevronDown size={12} />
        </button>
      )}
      {open === name && (
        <div
          id={`menu-${name}`}
          className={
            name === "account" || name === "ai" ? "fh-dropdown" : "fh-mega"
          }
        >
          {children}
        </div>
      )}
    </div>
  );
}
export function ScoreboardStrip({ sport = "Football" }: { sport?: Sport }) {
  const { data, isPending, error, refetch } = useFixtures(sport);
  return (
    <section className="fh-scorebar" aria-label="Scoreboard">
      <div className="fh-score-label">
        <Activity size={14} />
        <span>SCOREBOARD</span>
        <small>Latest available data</small>
      </div>
      <div className="fh-score-scroll">
        {isPending ? (
          <p role="status">Loading fixtures…</p>
        ) : error ? (
          <p>
            Scores unavailable{" "}
            <button onClick={() => void refetch()}>Retry</button>
          </p>
        ) : !data?.length ? (
          <p>No fixtures available.</p>
        ) : (
          data.slice(0, 12).map((match) => (
            <Link
              className="fh-ticker"
              key={match.id}
              to={`${sportPath(match.sport, "scores")}?match=${encodeURIComponent(match.id)}`}
            >
              <span>
                {match.league || match.sport}
                <small>{match.status || "Status unavailable"}</small>
              </span>
              <span>
                {match.home}
                <b>{match.homeScore ?? "—"}</b>
              </span>
              <span>
                {match.away}
                <b>{match.awayScore ?? "—"}</b>
              </span>
              <small>{formatDate(match.date)}</small>
            </Link>
          ))
        )}
      </div>
    </section>
  );
}
export default function MainNavbar() {
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuthStore();
  const [open, setOpen] = useState("");
  const [mobile, setMobile] = useState(false);
  const [wallet, setWallet] = useState(false);
  const header = useRef<HTMLElement>(null);
  const mobileTrigger = useRef<HTMLButtonElement>(null);
  const selected = sports.find(
    (sport) =>
      location.pathname.split("/")[1] === "sport" &&
      location.pathname.split("/")[2] === slug(sport),
  );
  const section = location.pathname.split("/")[3] || "home";
  useLayoutEffect(() => {
    setOpen("");
    setMobile(false);
  }, [location.pathname, location.search]);
  useEffect(() => {
    function outside(event: PointerEvent) {
      if (!header.current?.contains(event.target as Node)) {
        setOpen("");
        setMobile(false);
      }
    }
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, []);
  const initials =
    [user?.first_name?.[0], user?.last_name?.[0]].join("") ||
    user?.email?.[0]?.toUpperCase() ||
    "U";
  const accountLinks = (
    <>
      {isAuthenticated ? (
        <>
          <Link to="/profile">Profile</Link>
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/odds">Odds & betting</Link>
          <Link to="/bets">Bet history</Link>
          <Link to="/parlay-calculator">Parlay calculator</Link>
          <button
            onClick={() => {
              setWallet(true);
              setOpen("");
              setMobile(false);
            }}
          >
            Wallet
          </button>
          {(user?.is_admin || user?.is_super_admin) && (
            <Link to="/admin">Administration</Link>
          )}
          <button onClick={logout}>Log out</button>
        </>
      ) : (
        <>
          <Link to="/login">Log in</Link>
          <Link to="/register">Create account</Link>
        </>
      )}
    </>
  );
  return (
    <>
      <ScoreboardStrip sport={selected} />
      <header
        className="fh-nav"
        ref={header}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            const group = (event.target as HTMLElement).closest(
              ".fh-menu-group",
            );
            (
              group?.querySelector(
                ".fh-menu-trigger, button",
              ) as HTMLElement | null
            )?.focus();
            setOpen("");
            if (mobile) mobileTrigger.current?.focus();
            setMobile(false);
          }
        }}
      >
        <div className="fh-nav-inner">
          <Brand to="/app" />
          <nav className="fh-desktop-nav" aria-label="Sports">
            {sports.map((sport) => (
              <MenuGroup
                key={sport}
                name={slug(sport)}
                destination={sportPath(sport)}
                label={
                  <span className={selected === sport ? "active" : ""}>
                    {sport}
                  </span>
                }
                open={open}
                setOpen={setOpen}
              >
                <div className="fh-mega-quick">
                  <h3>{sport}</h3>
                  {sections.map((item) => (
                    <Link key={item} to={sportPath(sport, item.toLowerCase())}>
                      {item}
                      <ArrowUpRight size={12} />
                    </Link>
                  ))}
                </div>
                <div className="fh-mega-columns">
                  {Object.entries(leagues[sport]).map(([league, teams]) => (
                    <div key={league}>
                      <Link
                        className="fh-league-heading"
                        to={`${sportPath(sport, "schedule")}?competition=${encodeURIComponent(league)}`}
                      >
                        {league}
                      </Link>
                      {teams.map((team) => (
                        <Link
                          key={team}
                          to={`${sportPath(sport, "teams")}?team=${encodeURIComponent(team)}`}
                        >
                          {team}
                        </Link>
                      ))}
                    </div>
                  ))}
                </div>
              </MenuGroup>
            ))}
          </nav>
          <div className="fh-nav-actions">
            <MenuGroup
              name="ai"
              label={
                <>
                  <Sparkles size={14} />
                  AI Picks
                </>
              }
              open={open}
              setOpen={setOpen}
            >
              <Link to="/ai-picks">Best picks</Link>
              <Link to="/ai-picks/chat">Chat</Link>
            </MenuGroup>
            <MenuGroup
              name="account"
              label={
                <span
                  className="fh-avatar"
                  aria-label={
                    isAuthenticated
                      ? `Account for ${user?.first_name || user?.email || "user"}`
                      : "Account menu"
                  }
                >
                  {isAuthenticated ? initials : <UserRound size={17} />}
                </span>
              }
              open={open}
              setOpen={setOpen}
            >
              {accountLinks}
            </MenuGroup>
            <button
              ref={mobileTrigger}
              className="fh-mobile-toggle"
              aria-label={mobile ? "Close navigation" : "Open navigation"}
              aria-expanded={mobile}
              aria-controls="mobile-navigation"
              onClick={() => {
                setMobile(!mobile);
                setOpen("");
              }}
            >
              {mobile ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
        {mobile && (
          <nav
            id="mobile-navigation"
            className="fh-mobile-menu"
            aria-label="Mobile navigation"
          >
            {sports.map((sport) => (
              <details key={sport}>
                <summary>{sport}</summary>
                <Link to={sportPath(sport)}>Visit {sport}</Link>
                {sections.slice(1).map((item) => (
                  <Link key={item} to={sportPath(sport, item.toLowerCase())}>
                    {item}
                  </Link>
                ))}
                {Object.keys(leagues[sport]).map((league) => (
                  <Link
                    key={league}
                    to={`${sportPath(sport, "teams")}?competition=${encodeURIComponent(league)}`}
                  >
                    {league}
                  </Link>
                ))}
              </details>
            ))}
            <details>
              <summary>AI Picks</summary>
              <Link to="/ai-picks">Best picks</Link>
              <Link to="/ai-picks/chat">Chat</Link>
            </details>
            <details>
              <summary>Account</summary>
              {accountLinks}
            </details>
          </nav>
        )}
      </header>
      {selected && (
        <nav className="fh-subnav" aria-label={`${selected} navigation`}>
          <span>{selected.toUpperCase()}</span>
          {sections.map((item) => (
            <Link
              key={item}
              className={section === item.toLowerCase() ? "selected" : ""}
              aria-current={section === item.toLowerCase() ? "page" : undefined}
              to={sportPath(selected, item.toLowerCase())}
            >
              {item}
            </Link>
          ))}
        </nav>
      )}
      {wallet && (
        <WalletModal
          isOpen={wallet}
          onClose={() => setWallet(false)}
          currentBalance={user?.balance || 0}
          restoreFocus={() =>
            header.current?.querySelector<HTMLElement>(
              window.matchMedia("(max-width: 850px)").matches
                ? ".fh-mobile-toggle"
                : 'button[aria-controls="menu-account"]',
            ) || null
          }
        />
      )}
    </>
  );
}
