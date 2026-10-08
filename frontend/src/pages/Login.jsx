import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useLogin } from "../hooks/useAuth";
import { loginSchema, safeParse } from "../utils/validation";
import { sanitize } from "../utils/api";

import { AuthLayout, AuthField, AuthSubmit } from "../landing/AuthForms";

const Login = () => {
  const location = useLocation();
  const loginMutation = useLogin();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);

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
      result.error.issues.forEach((err) => {
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

      // PublicRoute owns the authenticated redirect. Multiple competing
      // navigations here previously reset menus after the dashboard opened.
    } catch (error) {
      setErrors({ submit: error.message || "Login failed" });
    }
  };

  return (
    <AuthLayout
      title="Welcome back."
      description="Log in to follow your teams and pick up where you left off."
      footer={
        <p>
          Don't have an account?{" "}
          <Link
            to={{ pathname: "/register", search: location.search }}
            state={location.state}
          >
            Register here
          </Link>
        </p>
      }
    >
      <form
        onSubmit={handleSubmit}
        noValidate
        aria-busy={loginMutation.isPending}
      >
        <AuthField
          name="email"
          label="Email Address"
          type="email"
          value={formData.email}
          onChange={handleChange}
          placeholder="you@example.com"
          autoComplete="email"
          required
          disabled={loginMutation.isPending}
          error={errors.email}
        />
        <AuthField
          name="password"
          label="Password"
          type={showPassword ? "text" : "password"}
          value={formData.password}
          onChange={handleChange}
          placeholder="Enter your password"
          autoComplete="current-password"
          required
          disabled={loginMutation.isPending}
          error={errors.password}
          passwordVisible={showPassword}
          onToggleVisibility={() => setShowPassword(!showPassword)}
        />
        {errors.submit && (
          <p className="auth-error auth-server-error" role="alert">
            {errors.submit}
          </p>
        )}
        <AuthSubmit
          pending={loginMutation.isPending}
          label="Login"
          pendingLabel="Logging in..."
        />
      </form>
    </AuthLayout>
  );
};

export default Login;
