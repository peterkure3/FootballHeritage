import { memo, useState } from 'react';
import { usePlaceBet } from '../hooks/useBetting';
import useBettingStore from '../stores/bettingStore';
import { betSchema, safeParse } from '../utils/validation';
import { sanitize } from '../utils/api';

const BetConfirmationModal = memo(({ isOpen, onClose, betDetails }) => {
  const [betAmount, setBetAmount] = useState('');
  const [errors, setErrors] = useState({});

  const placeBetMutation = usePlaceBet();
  const { getRemainingBudget, isNearLimit, isAtLimit, getSessionStats } = useBettingStore();

  const isLoading = placeBetMutation.isPending;

  // Close modal and reset
  const handleClose = () => {
    if (isLoading) return;
    setBetAmount('');
    setErrors({});
    onClose();
  };

  // Handle amount change
  const handleAmountChange = (e) => {
    const value = e.target.value;
    // Allow only numbers and decimal point
    if (value === '' || /^\d*\.?\d{0,2}$/.test(value)) {
      setBetAmount(value);
      if (value) {
        validateBet(value);
      } else {
        setErrors({});
      }
    }
  };

  // Validate bet
  const validateBet = (amount) => {
    if (!betDetails) return false;

    const sanitizedAmount = sanitize.amount(amount);
    const result = safeParse(betSchema, {
      eventId: betDetails.eventId,
      amount: sanitizedAmount,
      odds: betDetails.odds,
      type: betDetails.type,
    });

    if (!result.success) {
      const fieldErrors = {};
      result.error.errors.forEach((err) => {
        fieldErrors[err.path[0]] = err.message;
      });
      setErrors(fieldErrors);
      return false;
    }

    // Check session limits
    const remaining = getRemainingBudget();
    if (sanitizedAmount > remaining) {
      setErrors({ amount: `Exceeds session limit. Remaining: $${remaining.toFixed(2)}` });
      return false;
    }

    setErrors({});
    return true;
  };

  // Quick amount buttons
  const quickAmounts = [5, 10, 25, 50];

  const handleQuickAmount = (amount) => {
    setBetAmount(amount.toString());
    validateBet(amount);
  };

  // Calculate potential payout
  const calculatePayout = () => {
    if (!betAmount || !betDetails?.odds) return 0;
    const amount = parseFloat(betAmount) || 0;
    const odds = parseFloat(betDetails.odds) || 0;
    return (amount * odds).toFixed(2);
  };

  // Handle bet placement
  const handlePlaceBet = async () => {
    if (!betDetails) return;

    const sanitizedAmount = sanitize.amount(betAmount);

    if (!validateBet(sanitizedAmount)) {
      return;
    }

    try {
      await placeBetMutation.mutateAsync({
        eventId: betDetails.eventId,
        amount: sanitizedAmount,
        odds: betDetails.odds,
        type: betDetails.type,
      });

      // Success - close modal
      setBetAmount('');
      setErrors({});
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (error) {
      setErrors({ submit: error.message });
    }
  };

  if (!isOpen || !betDetails) return null;

  const potentialPayout = calculatePayout();
  const sessionStats = getSessionStats();
  const showWarning = isNearLimit();
  const atLimit = isAtLimit();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-gray-800 rounded-xl shadow-2xl border border-gray-700 w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-green-700 p-6 relative">
          <h2 className="text-white text-2xl font-bold">Place Your Bet</h2>
          <p className="text-green-100 text-sm mt-1">Confirm bet details</p>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="absolute top-4 right-4 text-white hover:text-gray-200 transition-colors disabled:opacity-50"
            aria-label="Close modal"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Event Details */}
          <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-4 mb-4">
            <h3 className="text-white font-bold text-lg mb-2">{betDetails.eventName}</h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-400">Bet Type:</span>
                <span className="text-white font-semibold ml-2">
                  {betDetails.type?.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Odds:</span>
                <span className="text-green-400 font-bold ml-2">{betDetails.odds}x</span>
              </div>
            </div>
          </div>

          {/* Amount Input */}
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-semibold mb-2">
              Bet Amount ($)
            </label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg font-bold">
                $
              </span>
              <input
                type="text"
                value={betAmount}
                onChange={handleAmountChange}
                placeholder="0.00"
                disabled={isLoading || atLimit}
                autoFocus
                className={`w-full pl-10 pr-4 py-3 bg-gray-900 border rounded-lg text-white text-lg font-semibold placeholder-gray-500 focus:outline-none focus:ring-2 transition-all ${
                  errors.amount
                    ? 'border-red-500 focus:ring-red-500'
                    : 'border-gray-700 focus:ring-green-500'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              />
            </div>
            {errors.amount && (
              <p className="text-red-400 text-xs mt-2 flex items-center">
                <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                {errors.amount}
              </p>
            )}
          </div>

          {/* Quick Amount Buttons */}
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-semibold mb-2">
              Quick Select
            </label>
            <div className="grid grid-cols-4 gap-2">
              {quickAmounts.map((amount) => {
                const remaining = getRemainingBudget();
                const isDisabled = isLoading || atLimit || amount > remaining;
                return (
                  <button
                    key={amount}
                    type="button"
                    onClick={() => handleQuickAmount(amount)}
                    disabled={isDisabled}
                    className={`py-2 px-3 rounded-lg font-semibold text-sm transition-all ${
                      betAmount === amount.toString()
                        ? 'bg-green-500 text-white shadow-lg'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    ${amount}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Session Limit Warning */}
          {showWarning && !atLimit && (
            <div className="bg-yellow-500/10 border border-yellow-500 rounded-lg p-3 mb-4">
              <p className="text-yellow-400 text-xs flex items-center">
                <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                Approaching session limit: ${sessionStats.remaining.toFixed(2)} remaining
              </p>
            </div>
          )}

          {/* At Limit Warning */}
          {atLimit && (
            <div className="bg-red-500/10 border border-red-500 rounded-lg p-3 mb-4">
              <p className="text-red-400 text-xs flex items-center">
                <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
                Session limit reached ($100). Please take a break.
              </p>
            </div>
          )}

          {/* Bet Summary */}
          <div className="bg-gray-900 rounded-lg p-4 mb-4">
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Bet Amount:</span>
                <span className="text-white font-semibold">${betAmount || '0.00'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Odds:</span>
                <span className="text-white font-semibold">{betDetails.odds}x</span>
              </div>
              <div className="border-t border-gray-700 pt-2 flex justify-between">
                <span className="text-gray-400">Potential Payout:</span>
                <span className="text-green-400 font-bold text-lg">${potentialPayout}</span>
              </div>
            </div>
          </div>

          {/* Session Stats */}
          <div className="bg-blue-500/10 border border-blue-500/50 rounded-lg p-3 mb-4">
            <div className="flex justify-between items-center text-xs">
              <span className="text-blue-300">Session: ${sessionStats.total.toFixed(2)} / ${sessionStats.limit}</span>
              <span className="text-blue-300">{sessionStats.percentUsed}% used</span>
            </div>
            <div className="mt-2 bg-gray-900 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  sessionStats.percentUsed >= 80 ? 'bg-red-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(sessionStats.percentUsed, 100)}%` }}
              />
            </div>
          </div>

          {/* Submit Error */}
          {errors.submit && (
            <div className="bg-red-500/10 border border-red-500 rounded-lg p-3 mb-4">
              <p className="text-red-400 text-sm">{errors.submit}</p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleClose}
              disabled={isLoading}
              className="flex-1 py-3 px-4 bg-gray-700 text-white rounded-lg font-semibold hover:bg-gray-600 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handlePlaceBet}
              disabled={isLoading || !betAmount || Object.keys(errors).length > 0 || atLimit}
              className="flex-1 py-3 px-4 bg-green-500 text-white rounded-lg font-bold hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-green-500/30 active:scale-95"
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Placing...
                </span>
              ) : (
                `Place Bet - $${betAmount || '0.00'}`
              )}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-900 px-6 py-3 border-t border-gray-700">
          <p className="text-gray-500 text-xs text-center">
            🎰 Gamble responsibly • Set limits • Know when to stop
          </p>
        </div>
      </div>
    </div>
  );
});

BetConfirmationModal.displayName = 'BetConfirmationModal';

export default BetConfirmationModal;
