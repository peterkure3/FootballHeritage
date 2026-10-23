import { Link } from "react-router-dom";
import AdminPage from "./AdminPage";

export default function BetAvailability() {
  return (
    <AdminPage
      title="Bet management."
      description="Platform bet administration."
    >
      <div className="admin-notice">
        <strong>Bet administration is unavailable.</strong>
        <p>
          The backend admin bet routes are disabled. Settlement and void actions
          will be available when that service is enabled.
        </p>
      </div>
      <article className="admin-panel">
        <h2>Review current activity</h2>
        <p>
          Platform statistics show today's bet count and stakes. Paper trials
          have their own prediction ledger and do not settle money bets.
        </p>
        <div className="admin-toolbar">
          <Link className="admin-button" to="/admin/analytics">
            Platform statistics
          </Link>
          <Link className="admin-button" to="/predictions?view=trials">
            Paper trial ledger
          </Link>
        </div>
      </article>
    </AdminPage>
  );
}
