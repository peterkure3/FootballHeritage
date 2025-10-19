import { memo } from 'react';
import { getAge } from '../utils/validation';

const AgeVerificationModal = memo(({ isOpen, dob, onConfirm, onCancel }) => {
  if (!isOpen) return null;

  const age = dob ? getAge(dob) : 0;
  const isOldEnough = age >= 21;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md">
      <div className="bg-gray-800 rounded-xl shadow-2xl border-2 border-yellow-500 w-full max-w-lg overflow-hidden animate-fadeIn">
        {/* Warning Header */}
        <div className="bg-gradient-to-r from-yellow-600 to-orange-600 p-6 text-center">
          <div className="text-6xl mb-2">⚠️</div>
          <h2 className="text-white text-2xl font-bold">Age Verification Required</h2>
          <p className="text-yellow-100 text-sm mt-2">
            Sports betting is restricted to adults 21 and over
          </p>
        </div>

        {/* Content */}
        <div className="p-8">
          {isOldEnough ? (
            <>
              {/* Age Confirmed */}
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-green-500/20 rounded-full mb-4">
                  <svg
                    className="w-10 h-10 text-green-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <h3 className="text-white text-xl font-bold mb-2">Age Verified</h3>
                <p className="text-gray-300 text-sm">
                  You are <span className="text-green-400 font-bold">{age} years old</span> and eligible to participate in sports betting.
                </p>
              </div>

              {/* Legal Disclaimer */}
              <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-4 mb-6">
                <h4 className="text-yellow-400 text-sm font-bold mb-2 flex items-center">
                  <svg
                    className="w-4 h-4 mr-2"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Important Information
                </h4>
                <ul className="text-gray-300 text-xs space-y-1">
                  <li>• You must be 21+ to place bets</li>
                  <li>• Gambling can be addictive - play responsibly</li>
                  <li>• Set limits and stick to them</li>
                  <li>• Never bet more than you can afford to lose</li>
                  <li>• Session limit: $100 per session</li>
                </ul>
              </div>

              {/* Responsible Gambling Resources */}
              <div className="bg-blue-500/10 border border-blue-500/50 rounded-lg p-3 mb-6">
                <p className="text-blue-300 text-xs text-center">
                  <strong>Need help?</strong> Contact the National Problem Gambling Helpline:
                  <span className="block mt-1 font-bold">1-800-522-4700</span>
                </p>
              </div>

              {/* Confirmation Checkbox Info */}
              <div className="text-center text-gray-400 text-xs mb-6">
                By proceeding, you confirm that:
                <ul className="mt-2 space-y-1">
                  <li>✓ You are at least 21 years old</li>
                  <li>✓ You agree to gamble responsibly</li>
                  <li>✓ You understand the risks involved</li>
                </ul>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={onCancel}
                  className="flex-1 py-3 px-4 bg-gray-700 text-white rounded-lg font-semibold hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={onConfirm}
                  className="flex-1 py-3 px-4 bg-green-500 text-white rounded-lg font-semibold hover:bg-green-600 transition-colors shadow-lg shadow-green-500/30"
                >
                  I Confirm - Proceed
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Age Not Met */}
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-red-500/20 rounded-full mb-4">
                  <svg
                    className="w-10 h-10 text-red-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </div>
                <h3 className="text-white text-xl font-bold mb-2">Access Denied</h3>
                <p className="text-gray-300 text-sm mb-4">
                  {dob && age > 0 ? (
                    <>
                      You are currently <span className="text-red-400 font-bold">{age} years old</span>.
                    </>
                  ) : (
                    <>Please provide a valid date of birth.</>
                  )}
                </p>
                <p className="text-gray-400 text-sm">
                  You must be at least 21 years old to access this sports betting platform.
                </p>
              </div>

              {/* Legal Notice */}
              <div className="bg-red-500/10 border border-red-500 rounded-lg p-4 mb-6">
                <h4 className="text-red-400 text-sm font-bold mb-2">Legal Requirements</h4>
                <p className="text-gray-300 text-xs">
                  Federal and state laws prohibit sports betting for individuals under 21 years of age.
                  This is to protect minors from gambling-related harm.
                </p>
              </div>

              {/* Resources for Young People */}
              <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-4 mb-6">
                <h4 className="text-gray-300 text-sm font-semibold mb-2">Resources</h4>
                <p className="text-gray-400 text-xs">
                  If you or someone you know is struggling with gambling, help is available:
                </p>
                <p className="text-blue-400 text-xs mt-2 font-semibold">
                  National Council on Problem Gambling: ncpgambling.org
                </p>
              </div>

              {/* Action Button */}
              <button
                onClick={onCancel}
                className="w-full py-3 px-4 bg-gray-700 text-white rounded-lg font-semibold hover:bg-gray-600 transition-colors"
              >
                Go Back
              </button>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-900 px-6 py-3 border-t border-gray-700">
          <p className="text-gray-500 text-xs text-center">
            🔒 Your information is secure and confidential
          </p>
        </div>
      </div>
    </div>
  );
});

AgeVerificationModal.displayName = 'AgeVerificationModal';

export default AgeVerificationModal;
