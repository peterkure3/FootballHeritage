import { useState, memo } from 'react';
import { useDeposit, useWithdraw } from '../hooks/useBetting';
import { depositSchema, withdrawSchema, safeParse } from '../utils/validation';
import { sanitize } from '../utils/api';
import { Dialog } from '../heritage/ui';

const WalletModal = memo(({ isOpen, onClose, initialTab = 'deposit', currentBalance = 0, restoreFocus }) => {
  const [activeTab, setActiveTab] = useState(initialTab);
  const [amount, setAmount] = useState('');
  const [errors, setErrors] = useState({});

  const depositMutation = useDeposit();
  const withdrawMutation = useWithdraw();

  const isLoading = depositMutation.isPending || withdrawMutation.isPending;

  // Close modal
  const handleClose = () => {
    if (isLoading) return;
    setAmount('');
    setErrors({});
    onClose();
  };

  // Handle tab switch
  const handleTabSwitch = (tab) => {
    setActiveTab(tab);
    setAmount('');
    setErrors({});
  };

  // Validate amount
  const validateAmount = (value) => {
    const sanitizedAmount = sanitize.amount(value);
    const schema = activeTab === 'deposit' ? depositSchema : withdrawSchema;
    const result = safeParse(schema, { amount: sanitizedAmount });

    if (!result.success) {
      const fieldErrors = {};
      result.error.issues.forEach((err) => {
        fieldErrors[err.path[0]] = err.message;
      });
      setErrors(fieldErrors);
      return false;
    }

    setErrors({});
    return true;
  };

  // Handle amount change
  const handleAmountChange = (e) => {
    const value = e.target.value;
    // Allow only numbers and decimal point
    if (value === '' || /^\d*\.?\d{0,2}$/.test(value)) {
      setAmount(value);
      if (value) {
        validateAmount(value);
      } else {
        setErrors({});
      }
    }
  };

  // Quick amount buttons
  const quickAmounts = [10, 25, 50, 100];

  const handleQuickAmount = (quickAmount) => {
    setAmount(quickAmount.toString());
    validateAmount(quickAmount);
  };

  // Handle submit
  const handleSubmit = async (e) => {
    e.preventDefault();

    const sanitizedAmount = sanitize.amount(amount);

    if (!validateAmount(sanitizedAmount)) {
      return;
    }

    // Additional validation for withdrawals
    if (activeTab === 'withdraw') {
      if (sanitizedAmount > currentBalance) {
        setErrors({ amount: 'Insufficient balance' });
        return;
      }
    }

    try {
      if (activeTab === 'deposit') {
        await depositMutation.mutateAsync(sanitizedAmount);
      } else {
        await withdrawMutation.mutateAsync(sanitizedAmount);
      }

      // Success - close modal and reset
      setAmount('');
      setErrors({});
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (error) {
      setErrors({ submit: error.message });
    }
  };

  if (!isOpen) return null;

  return (
    <Dialog title="Wallet" className="fh-wallet-dialog" onClose={handleClose} restoreFocus={restoreFocus}>
      <div className="bg-card rounded-xl shadow-2xl border border-card-border w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-green-700 p-6 relative">
          <h2 className="text-white text-2xl font-normal">Wallet</h2>
          <p className="text-green-100 text-sm mt-1">
            Current Balance: <span className="font-bold">${currentBalance.toFixed(2)}</span>
          </p>
          <button
            onClick={handleClose}
            disabled={isLoading}
            aria-label="Close wallet modal"
            className="absolute top-4 right-4 text-white hover:text-white transition-colors disabled:opacity-50"
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

        {/* Tabs */}
        <div className="flex border-b border-card-border">
          <button
            onClick={() => handleTabSwitch('deposit')}
            disabled={isLoading}
            className={`flex-1 py-4 px-6 font-semibold transition-colors ${
              activeTab === 'deposit'
                ? 'bg-card text-green-700 border-b-2 border-green-400'
                : 'text-heritage-muted hover:text-heritage-ink hover:bg-gray-750'
            } disabled:opacity-50`}
          >
            💰 Deposit
          </button>
          <button
            onClick={() => handleTabSwitch('withdraw')}
            disabled={isLoading}
            className={`flex-1 py-4 px-6 font-semibold transition-colors ${
              activeTab === 'withdraw'
                ? 'bg-card text-green-700 border-b-2 border-green-400'
                : 'text-heritage-muted hover:text-heritage-ink hover:bg-gray-750'
            } disabled:opacity-50`}
          >
            💸 Withdraw
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Amount Input */}
            <div>
              <label className="block text-heritage-ink text-sm font-semibold mb-2">
                Amount ($)
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-heritage-muted text-lg font-bold">
                  $
                </span>
                <input
                  type="text"
                  value={amount}
                  onChange={handleAmountChange}
                  placeholder="0.00"
                  disabled={isLoading}
                  className={`w-full pl-10 pr-4 py-3 bg-card border rounded-lg text-heritage-ink text-lg font-semibold placeholder-gray-500 focus:outline-none focus:ring-2 transition-all ${
                    errors.amount
                      ? 'border-red-500 focus:ring-red-500'
                      : 'border-card-border focus:ring-green-500'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                />
              </div>
              {errors.amount && (
                <p className="text-red-700 text-xs mt-2 flex items-center">
                  <svg
                    className="w-4 h-4 mr-1"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
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
            <div>
              <label className="block text-heritage-ink text-sm font-semibold mb-2">
                Quick Select
              </label>
              <div className="grid grid-cols-4 gap-2">
                {quickAmounts.map((quickAmount) => (
                  <button
                    key={quickAmount}
                    type="button"
                    onClick={() => handleQuickAmount(quickAmount)}
                    disabled={isLoading || (activeTab === 'withdraw' && quickAmount > currentBalance)}
                    className={`py-2 px-3 rounded-lg font-semibold text-sm transition-all ${
                      amount === quickAmount.toString()
                        ? 'bg-green-500 text-white shadow-lg'
                        : 'bg-card-hover text-heritage-ink hover:bg-card-hover'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    ${quickAmount}
                  </button>
                ))}
              </div>
            </div>

            {/* Limits Info */}
            <div className="bg-card/50 rounded-lg p-4 border border-card-border">
              <h4 className="text-heritage-ink text-sm font-semibold mb-2">
                {activeTab === 'deposit' ? 'Deposit' : 'Withdrawal'} Limits
              </h4>
              <div className="space-y-1 text-xs text-heritage-muted">
                <div className="flex justify-between">
                  <span>Minimum:</span>
                  <span className="text-heritage-ink font-semibold">$10.00</span>
                </div>
                <div className="flex justify-between">
                  <span>Maximum:</span>
                  <span className="text-heritage-ink font-semibold">$10,000.00</span>
                </div>
                {activeTab === 'withdraw' && (
                  <div className="flex justify-between pt-2 border-t border-card-border mt-2">
                    <span>Available:</span>
                    <span className="text-green-700 font-semibold">
                      ${currentBalance.toFixed(2)}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Submit Error */}
            {errors.submit && (
              <div className="bg-red-500/10 border border-red-500 rounded-lg p-3">
                <p className="text-red-700 text-sm">{errors.submit}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || !amount || Object.keys(errors).length > 0}
              className={`w-full py-4 rounded-lg font-bold text-lg transition-all ${
                activeTab === 'deposit'
                  ? 'bg-green-500 hover:bg-green-600 text-white'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              } disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl active:scale-95`}
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg
                    className="animate-spin h-5 w-5 mr-2"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
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
                  Processing...
                </span>
              ) : (
                <>
                  {activeTab === 'deposit' ? '💰 Deposit' : '💸 Withdraw'} $
                  {amount || '0.00'}
                </>
              )}
            </button>
          </form>
        </div>

        {/* Security Notice */}
        <div className="bg-card px-6 py-4 border-t border-card-border">
          <p className="text-heritage-muted text-xs text-center">
            🔒 All transactions are encrypted and secure
          </p>
        </div>
      </div>
    </Dialog>
  );
});

WalletModal.displayName = 'WalletModal';

export default WalletModal;
