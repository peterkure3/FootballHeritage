import { Link } from "react-router-dom";

export default function Brand({
  to,
  label = "FootballHeritage homepage",
  className = "",
}: {
  to: string;
  label?: string;
  className?: string;
}) {
  return (
    <Link className={`fh-brand ${className}`} to={to} aria-label={label}>
      <span className="fh-brand-mark">
        fh<span>.</span>
      </span>
      <span className="fh-brand-name">
        FOOTBALL
        <br />
        <strong>HERITAGE</strong>
      </span>
    </Link>
  );
}
