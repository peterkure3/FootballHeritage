import { Link, useLocation } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import Brand from "../heritage/Brand";
import "./landing.css";

export default function LandingNavbar() {
  const location = useLocation();
  const onAuthPage = /^\/(login|register)\/?$/.test(location.pathname);
  const search = onAuthPage ? location.search : "";
  const state = onAuthPage ? location.state : undefined;

  return (
    <header className="landing-nav">
      <Brand to="/" label="FootballHeritage home" className="landing-brand" />
      <nav aria-label="Landing account navigation">
        <Link
          className="landing-register"
          to={{ pathname: "/register", search }}
          state={state}
        >
          Register <ArrowUpRight size={14} aria-hidden="true" />
        </Link>
        <Link
          className="landing-login"
          to={{ pathname: "/login", search }}
          state={state}
        >
          Login
        </Link>
      </nav>
    </header>
  );
}
