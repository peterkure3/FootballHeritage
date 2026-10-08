import { memo } from 'react';

const BetCard = memo(({ bet }) => {
  // Determine status styling
  const getStatusStyles = (status) => {
    switch (status?.toLowerCase()) {
      case 'won':
      case 'settled_won':
        return 'bg-green-500/20 text-green-700 border-green-500/50';
      case 'lost':
      case 'settled_lost':
        return 'bg-red-500/20 text-red-700 border-red-500/50';
      case 'pending':
      case 'active':
        return 'bg-yellow-500/20 text-yellow-700 border-yellow-500/50';
      case 'cancelled':
      case 'refunded':
        return 'bg-gray-500/20 text-heritage-muted border-gray-500/50';
      default:
        return 'bg-blue-500/20 text-blue-700 border-blue-500/50';
    }
  };

  // Format bet type
  const formatBetType = (type) => {
    if (!type) return 'Unknown';
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Invalid Date';
    }
  };

  // Calculate potential payout
  const calculatePayout = () => {
    const amount = parseFloat(bet.amount) || 0;
    const odds = parseFloat(bet.odds) || 0;
    return (amount * odds).toFixed(2);
  };

  const statusStyles = getStatusStyles(bet.status);
  const potentialPayout = calculatePayout();

  return (
    <div className="bg-card/50 border border-card-border rounded-lg p-4 hover:border-card-border transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-heritage-ink font-semibold text-lg mb-1">
            {bet.event_name || bet.eventName || `Event #${bet.event_id || bet.eventId}`}
          </h3>
          <p className="text-heritage-muted text-sm">
            {formatDate(bet.placed_at || bet.placedAt || bet.timestamp || bet.created_at)}
          </p>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold border ${statusStyles}`}
        >
          {bet.status?.toUpperCase() || 'PENDING'}
        </span>
      </div>

      {/* Bet Details */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <p className="text-heritage-muted text-xs mb-1">Bet Type</p>
          <p className="text-heritage-ink font-medium">{formatBetType(bet.type || bet.bet_type)}</p>
        </div>
        <div>
          <p className="text-heritage-muted text-xs mb-1">Odds</p>
          <p className="text-heritage-ink font-medium">{bet.odds ? `${bet.odds}x` : 'N/A'}</p>
        </div>
      </div>

      {/* Amount and Payout */}
      <div className="border-t border-card-border pt-3 grid grid-cols-2 gap-3">
        <div>
          <p className="text-heritage-muted text-xs mb-1">Stake</p>
          <p className="text-heritage-ink font-bold text-lg">
            ${parseFloat(bet.amount || 0).toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-heritage-muted text-xs mb-1">
            {bet.status === 'won' || bet.status === 'settled_won' ? 'Payout' : 'Potential'}
          </p>
          <p className="text-green-700 font-bold text-lg">
            {bet.payout ? `$${parseFloat(bet.payout).toFixed(2)}` : `$${potentialPayout}`}
          </p>
        </div>
      </div>

      {/* Additional Info */}
      {bet.selection && (
        <div className="mt-3 pt-3 border-t border-card-border">
          <p className="text-heritage-muted text-xs mb-1">Selection</p>
          <p className="text-heritage-ink text-sm">{bet.selection}</p>
        </div>
      )}

      {/* Bet ID */}
      {(bet.id || bet.bet_id) && (
        <div className="mt-2">
          <p className="text-heritage-muted text-xs">
            ID: {bet.id || bet.bet_id}
          </p>
        </div>
      )}
    </div>
  );
});

BetCard.displayName = 'BetCard';

export default BetCard;
