import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useRegister } from "../hooks/useAuth";
import AgeVerificationModal from "../components/AgeVerificationModal";
import { registerSchema, safeParse } from "../utils/validation";
import { sanitize } from "../utils/api";

import { AuthLayout, AuthField, AuthSubmit } from "../landing/AuthForms";

const Register = () => {
  const location = useLocation();
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
      result.error.issues.forEach((err) => {
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

      // PublicRoute owns the authenticated redirect and validated return URL.
    } catch (error) {
      setErrors({ submit: error.message || "Registration failed" });
    }
  };

  const handleAgeVerificationCancel = () => {
    setShowAgeVerification(false);
  };

  return (
    <>
      <AuthLayout
        registration
        title="Make the game yours."
        description="Create your FootballHeritage account."
        footer={
          <p>
            Already have an account?{" "}
            <Link
              to={{ pathname: "/login", search: location.search }}
              state={location.state}
            >
              Login here
            </Link>
          </p>
        }
      >
        <p className="auth-age-note">You must be 21 or older to register.</p>
        <form
          onSubmit={handleSubmit}
          noValidate
          aria-busy={registerMutation.isPending}
        >
          <div className="auth-name-row">
            <AuthField
              name="firstName"
              label="First Name"
              type="text"
              value={formData.firstName}
              onChange={handleChange}
              placeholder="First name"
              autoComplete="given-name"
              required
              disabled={registerMutation.isPending}
              error={errors.firstName}
            />
            <AuthField
              name="lastName"
              label="Last Name"
              type="text"
              value={formData.lastName}
              onChange={handleChange}
              placeholder="Last name"
              autoComplete="family-name"
              required
              disabled={registerMutation.isPending}
              error={errors.lastName}
            />
          </div>
          <AuthField
            name="email"
            label="Email Address"
            type="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="you@example.com"
            autoComplete="email"
            required
            disabled={registerMutation.isPending}
            error={errors.email}
          />
          <AuthField
            name="dob"
            label="Date of Birth"
            type="date"
            value={formData.dob}
            onChange={handleChange}
            max={new Date().toISOString().split("T")[0]}
            autoComplete="bday"
            required
            hint="Used to verify that you are at least 21 years old."
            disabled={registerMutation.isPending}
            error={errors.dob}
          />
          <AuthField
            name="password"
            label="Password"
            type={showPassword ? "text" : "password"}
            value={formData.password}
            onChange={handleChange}
            placeholder="Create a password"
            autoComplete="new-password"
            required
            hint="At least 8 characters, with uppercase, lowercase, a number and a special character."
            disabled={registerMutation.isPending}
            error={errors.password}
            passwordVisible={showPassword}
            onToggleVisibility={() => setShowPassword(!showPassword)}
          />
          <AuthField
            name="confirmPassword"
            label="Confirm Password"
            type={showConfirmPassword ? "text" : "password"}
            value={formData.confirmPassword}
            onChange={handleChange}
            placeholder="Re-enter your password"
            autoComplete="new-password"
            required
            disabled={registerMutation.isPending}
            error={errors.confirmPassword}
            passwordVisible={showConfirmPassword}
            onToggleVisibility={() =>
              setShowConfirmPassword(!showConfirmPassword)
            }
          />
          <div>
            <label className="auth-consent">
              <input
                type="checkbox"
                name="terms"
                checked={formData.terms}
                onChange={handleChange}
                disabled={registerMutation.isPending}
                aria-invalid={!!errors.terms}
                aria-describedby={errors.terms ? "terms-error" : undefined}
              />
              <span>
                I agree to the Terms of Service and Privacy Policy, and I
                confirm that I am at least 21 years old.
              </span>
            </label>
            {errors.terms && (
              <p id="terms-error" className="auth-error" role="alert">
                {errors.terms}
              </p>
            )}
          </div>
          {errors.submit && (
            <p className="auth-error auth-server-error" role="alert">
              {errors.submit}
            </p>
          )}
          <AuthSubmit
            pending={registerMutation.isPending}
            label="Create Account"
            pendingLabel="Creating account..."
          />
        </form>
      </AuthLayout>
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
