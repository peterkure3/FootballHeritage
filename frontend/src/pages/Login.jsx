import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useLogin } from '../hooks/useAuth';
import useAuthStore from '../stores/authStore';
import { loginSchema, safeParse } from '../utils/validation';
import { sanitize } from '../utils/api';

const Login = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const loginMutation = useLogin();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const validateForm = () => {
    const sanitizedData = {
      email: sanitize.email(formData.email),
      password: formData.password,
    };

    const result = safeParse(loginSchema, sanitizedData);

    if (!result.success) {
      const fieldErrors = {};
      result.error.errors.forEach((err) => {
        fieldErrors[err.path[0]] = err.message;
      });
      setErrors(fieldErrors);
      return false;
    }

    setErrors({});
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      await loginMutation.mutateAsync({
        email: sanitize.email(formData.email),
        password: formData.password,
      });

      navigate('/dashboard');
    } catch (error) {
      setErrors({ submit: error.message || 'Login failed' });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "var(--color-surface)" }}>
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAxMCAwIEwgMCAwIDAgMTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwwLjAzKSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-50"></div>

      <div className="relative w-full max-w-md" style={{ animation: 'slide-up 0.4s ease-out both' }}>
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl shadow-2xl shadow-green-500/50 mb-4">
            <span className="text-4xl">🏈</span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">
            Sports<span style={{ color: '#10b981' }}>Bet</span>
          </h1>
          <p className="text-sm" style={{ color: '#64748b' }}>Welcome back! Login to start betting</p>
        </div>

        <div className="card-glow rounded-2xl p-8 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <svg className="w-5 h-5" style={{ color: '#64748b' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                  </svg>
                </div>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="your@email.com"
                  disabled={loginMutation.isPending}
                  autoComplete="email"
                  autoFocus
                  required
                  aria-label="Email address"
                  aria-invalid={!!errors.email}
                  aria-describedby={errors.email ? 'email-error' : undefined}
                  className={`w-full pl-12 pr-4 py-3 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 transition-all ${
                    errors.email
                      ? 'focus:ring-red-500'
                      : 'focus:ring-green-500'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                  style={{
                    background: 'var(--color-card)',
                    border: errors.email ? '1px solid #ef4444' : '1px solid var(--color-card-border)',
                  }}
                />
              </div>
              {errors.email && (
                <p id="email-error" className="text-xs mt-2 flex items-center" style={{ color: '#fca5a5' }} role="alert">
                  <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  {errors.email}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <svg className="w-5 h-5" style={{ color: '#64748b' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Enter your password"
                  disabled={loginMutation.isPending}
                  autoComplete="current-password"
                  required
                  aria-label="Password"
                  aria-invalid={!!errors.password}
                  aria-describedby={errors.password ? 'password-error' : undefined}
                  className={`w-full pl-12 pr-12 py-3 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 transition-all ${
                    errors.password
                      ? 'focus:ring-red-500'
                      : 'focus:ring-green-500'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                  style={{
                    background: 'var(--color-card)',
                    border: errors.password ? '1px solid #ef4444' : '1px solid var(--color-card-border)',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center transition-colors"
                  style={{ color: '#64748b' }}
                >
                  {showPassword ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
              {errors.password && (
                <p id="password-error" className="text-xs mt-2 flex items-center" style={{ color: '#fca5a5' }} role="alert">
                  <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  {errors.password}
                </p>
              )}
            </div>

            {errors.submit && (
              <div className="rounded-lg p-3 border" style={{ background: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
                <p className="text-sm flex items-center" style={{ color: '#fca5a5' }}>
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  {errors.submit}
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={loginMutation.isPending}
              className="w-full py-3 px-4 text-white font-bold rounded-lg transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg active:scale-95"
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)', boxShadow: '0 10px 15px -3px rgba(16, 185, 129, 0.3)' }}
            >
              {loginMutation.isPending ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Logging in...
                </span>
              ) : (
                'Login'
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm" style={{ color: '#64748b' }}>
              Don't have an account?{' '}
              <Link to="/register" className="font-semibold transition-colors" style={{ color: '#10b981' }}>
                Register here
              </Link>
            </p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <p className="text-xs" style={{ color: '#475569' }}>
            🔒 Your connection is secure and encrypted
          </p>
        </div>

        <div className="mt-4 text-center">
          <p className="text-xs" style={{ color: '#475569' }}>
            Gamble responsibly. Must be 21+ to participate.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
