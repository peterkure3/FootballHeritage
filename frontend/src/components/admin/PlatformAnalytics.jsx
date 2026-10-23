import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { adminService } from "../../services/adminService";
import AdminPage, { AdminMetrics } from "./AdminPage";

const amount = (value) =>
  value == null
    ? "—"
    : Number(value).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });

export default function PlatformAnalytics({ revenue = false }) {
  const query = useQuery({
    queryKey: ["admin-platform-metrics"],
    queryFn: ({ signal }) => adminService.metrics(signal),
    retry: false,
    refetchInterval: 60000,
  });
  const data = query.data || {};
  const items = revenue
    ? [
        ["Today's stakes · account units", amount(data.bet_volume_today)],
        ["Today's settled net · account units", amount(data.revenue_today)],
        ["Bets placed today", data.total_bets_today],
      ]
    : [
        ["Active accounts", data.total_users],
        ["New accounts today", data.new_users_today],
        ["Accounts betting today", data.active_users_today],
        ["Bets placed today", data.total_bets_today],
        ["Live events", data.live_events],
        ["Upcoming events", data.upcoming_events],
      ];
  return (
    <AdminPage
      title={revenue ? "Revenue overview." : "Platform statistics."}
      description="Current-day platform totals from the betting database. Refreshes every minute."
      query={query}
    >
      <AdminMetrics items={items} />
      <article className="admin-panel">
        <h2>
          {revenue ? "How the figures are counted" : "Monitor the platform"}
        </h2>
        <p>
          {revenue
            ? "Stakes count bets placed today. Settled net counts stakes on won and lost bets settled today, less winning payouts. These are different cohorts; void and pending bets are excluded from settled net. Amounts use the database account units. Today follows the database timezone."
            : "Active accounts are enabled accounts. Accounts betting today counts distinct bettors, rather than website visitors. Today follows the database timezone."}
        </p>
        <div className="admin-toolbar">
          <Link className="admin-button" to="/admin/logs">
            Review audit activity
          </Link>
          <Link className="admin-button" to="/admin/dashboard">
            Live operations
          </Link>
          <Link className="admin-button" to="/predictions?view=history">
            Model outcomes
          </Link>
        </div>
      </article>
    </AdminPage>
  );
}

export function RevenueOverview() {
  return <PlatformAnalytics revenue />;
}
