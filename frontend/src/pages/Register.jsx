import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useRegister } from "../hooks/useAuth";
import useAuthStore from "../stores/authStore";
import AgeVerificationModal from "../components/AgeVerificationModal";
import { registerSchema, safeParse } from "../utils/validation";
import { sanitize } from "../utils/api";

const Register = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const registerMutation = useRegister();

  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    email: "",
    password: "",
    confirmPassword: "",
    dob: "",
    terms: false,
  });

  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [showAgeVerification, setShowAgeVerification] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard");
    }
  }, [isAuthenticated, navigate]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
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
      firstName: sanitize.text(formData.firstName),
      lastName: sanitize.text(formData.lastName),
      email: sanitize.email(formData.email),
      password: formData.password,
      confirmPassword: formData.confirmPassword,
      dob: formData.dob,
      terms: formData.terms,
    };

    const result = safeParse(registerSchema, sanitizedData);

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

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setShowAgeVerification(true);
  };

  const handleAgeVerificationConfirm = async () => {
    setShowAgeVerification(false);

    try {
      await registerMutation.mutateAsync({
        email: sanitize.email(formData.email),
        password: formData.password,
        firstName: sanitize.text(formData.firstName),
        lastName: sanitize.text(formData.lastName),
        dateOfBirth: formData.dob,
      });

      navigate("/dashboard");
    } catch (error) {
      setErrors({ submit: error.message || "Registration failed" });
    }
  };

  const handleAgeVerificationCancel = () => {
    setShowAgeVerification(false);
  };

  return (
    <>
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
            <p className="text-sm" style={{ color: '#64748b' }}>
              Create your account and start betting
            </p>
          </div>

          <div className="card-glow rounded-2xl p-6 border" style={{ background: 'linear-gradient(135deg, var(--color-card), var(--color-card-hover))', borderColor: 'var(--color-card-border)' }}>
            <div className="rounded-lg p-3 mb-6" style={{ background: 'rgba(234, 179, 8, 0.08)', border: '1px solid rgba(234, 179, 8, 0.3)' }}>
              <p className="text-sm text-center flex items-center justify-center" style={{ color: '#eab308' }}>
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                You must be 21 or older to register
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="firstName" className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>
                  First Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="w-5 h-5" style={{ color: '#64748b' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <input
                    type="text"
                    id="firstName"
                    name="firstName"
                    value={formData.firstName}
                    onChange={handleChange}
                    placeholder="John"
                    disabled={registerMutation.isPending}
                    autoComplete="given-name"
                    autoFocus
                    required
                    aria-label="First name"
                    aria-invalid={!!errors.firstName}
                    aria-describedby={errors.firstName ? 'firstName-error' : undefined}
                    className={`w-full pl-12 pr-4 py-3 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 transition-all ${
                      errors.firstName ? 'focus:ring-red-500' : 'focus:ring-green-500'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                    style={{
                      background: 'var(--color-card)',
                      border: errors.firstName ? '1px solid #ef4444' : '1px solid var(--color-card-border)',
                    }}
                  />
                </div>
                {errors.firstName && (
                  <p id="firstName-error" className="text-xs mt-2 flex items-center" style={{ color: '#fca5a5' }} role="alert">
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {errors.firstName}
                  </p>
                )}
              </div>

              <div>
                <label htmlFor="lastName" className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>
                  Last Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="w-5 h-5" style={{ color: '#64748b' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <input
                    type="text"
                    id="lastName"
                    name="lastName"
                    value={formData.lastName}
                    onChange={handleChange}
                    placeholder="Doe"
                    disabled={registerMutation.isPending}
                    autoComplete="family-name"
                    required
                    aria-label="Last name"
                    aria-invalid={!!errors.lastName}
                    aria-describedby={errors.lastName ? 'lastName-error' : undefined}
                    className={`w-full pl-12 pr-4 py-3 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 transition-all ${
                      errors.lastName ? 'focus:ring-red-500' : 'focus:ring-green-500'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                    style={{
                      background: 'var(--color-card)',
                      border: errors.lastName ? '1px solid #ef4444' : '1px solid var(--color-card-border)',
                    }}
                  />
                </div>
                {errors.lastName && (
                  <p id="lastName-error" className="text-xs mt-2 flex items-center" style={{ color: '#fca5a5' }} role="alert">
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {errors.lastName}
                  </p>
                )}
              </div>

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
                    disabled={registerMutation.isPending}
                    autoComplete="email"
                    required
                    aria-label="Email address"
                    aria-invalid={!!errors.email}
                    aria-describedby={errors.email ? 'email-error' : undefined}
                    className={`w-full pl-12 pr-4 py-3 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 transition-all ${
                      errors.email ? 'focus:ring-red-500' : 'focus:ring-green-500'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                    style={{
                      background: 'var(--color-card)',
                      border: errors.email ? '1px solid #ef4444' : '1px solid var(--color-card-border)',
                    }}
                  />
                </div>
                {errors.email && (
                  <p className="text-xs mt-2 flex items-center" style={{ color: '#fca5a5' }}>
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {errors.email}
                  </p>
                )}
              </div>

              <div>
                <label htmlFor="dob" className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>
                  Date of Birth <span style={{ color: '#fca5a5' }}>*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="w-5 h-5" style={{ color: '#64748b' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <input
                    type="date"
                    id="dob"
                    name="dob"
                    value={formData.dob}
                    onChange={handleChange}
                    max={new Date().toISOString().split("T")[0]}
                    disabled={registerMutation.isPending}
                    className={`w-full pl-12 pr-4 py-3 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 transition-all ${
                      errors.dob ? 'focus:ring-red-500' : 'focus:ring-green-500'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                    style={{
                      background: 'var(--color-card)',
                      border: errors.dob ? '1px solid #ef4444' : '1px solid var(--color-card-border)',
                    }}
                  />
                </div>
                {errors.dob && (
                  <p className="text-xs mt-2 flex items-center" style={{ color: '#fca5a5' }}>
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {errors.dob}
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
                    type={showPassword ? "text" : "password"}
                    id="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="Min. 8 characters"
                    disabled={registerMutation.isPending}
                    className={`w-full pl-12 pr-12 py-3 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 transition-all ${
                      errors.password ? 'focus:ring-red-500' : 'focus:ring-green-500'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                    style={{
                      background: 'var(--color-card)',
                      border: errors.password ? '1px solid #ef4444' : '1px solid var(--color-card-border)',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
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
                  <p className="text-xs mt-2 flex items-center" style={{ color: '#fca5a5' }}>
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {errors.password}
                  </p>
                )}
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-semibold mb-2" style={{ color: '#94a3b8' }}>
                  Confirm Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="w-5 h-5" style={{ color: '#64748b' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    id="confirmPassword"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    placeholder="Re-enter password"
                    disabled={registerMutation.isPending}
                    className={`w-full pl-12 pr-12 py-3 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 transition-all ${
                      errors.confirmPassword ? 'focus:ring-red-500' : 'focus:ring-green-500'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                    style={{
                      background: 'var(--color-card)',
                      border: errors.confirmPassword ? '1px solid #ef4444' : '1px solid var(--color-card-border)',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center transition-colors"
                    style={{ color: '#64748b' }}
                  >
                    {showConfirmPassword ? (
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
                {errors.confirmPassword && (
                  <p className="text-xs mt-2 flex items-center" style={{ color: '#fca5a5' }}>
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {errors.confirmPassword}
                  </p>
                )}
              </div>

              <div>
                <label className="flex items-start cursor-pointer">
                  <input
                    type="checkbox"
                    name="terms"
                    checked={formData.terms}
                    onChange={handleChange}
                    disabled={registerMutation.isPending}
                    className="mt-1 w-4 h-4 rounded focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ accentColor: '#10b981' }}
                  />
                  <span className="ml-3 text-sm" style={{ color: '#cbd5e1' }}>
                    I agree to the{" "}
                    <a href="#" className="transition-colors" style={{ color: '#10b981' }}>
                      Terms of Service
                    </a>{" "}
                    and{" "}
                    <a href="#" className="transition-colors" style={{ color: '#10b981' }}>
                      Privacy Policy
                    </a>
                    , and I confirm that I am at least 21 years old.
                  </span>
                </label>
                {errors.terms && (
                  <p className="text-xs mt-2 flex items-center" style={{ color: '#fca5a5' }}>
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {errors.terms}
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
                disabled={registerMutation.isPending}
                className="w-full py-3 px-4 text-white font-bold rounded-lg transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg active:scale-95"
                style={{ background: 'linear-gradient(135deg, #10b981, #059669)', boxShadow: '0 10px 15px -3px rgba(16, 185, 129, 0.3)' }}
              >
                {registerMutation.isPending ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Creating account...
                  </span>
                ) : (
                  "Create Account"
                )}
              </button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm" style={{ color: '#64748b' }}>
                Already have an account?{" "}
                <Link to="/login" className="font-semibold transition-colors" style={{ color: '#10b981' }}>
                  Login here
                </Link>
              </p>
            </div>
          </div>

          <div className="mt-6 text-center">
            <p className="text-xs" style={{ color: '#475569' }}>
              🔒 Your information is secure and encrypted
            </p>
          </div>

          <div className="mt-4 text-center">
            <p className="text-xs" style={{ color: '#475569' }}>
              Gamble responsibly. Help available at{" "}
              <a href="tel:1-800-522-4700" className="transition-colors" style={{ color: '#60a5fa' }}>
                1-800-522-4700
              </a>
            </p>
          </div>
        </div>
      </div>

      <AgeVerificationModal
        isOpen={showAgeVerification}
        dob={formData.dob}
        onConfirm={handleAgeVerificationConfirm}
        onCancel={handleAgeVerificationCancel}
      />
    </>
  );
};

export default Register;
