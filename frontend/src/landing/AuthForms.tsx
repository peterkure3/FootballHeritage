import type { InputHTMLAttributes, ReactNode } from "react";
import { ArrowRight, Eye, EyeOff, LoaderCircle } from "lucide-react";
import "./auth.css";

export function AuthLayout({
  title,
  description,
  children,
  footer,
  registration = false,
}: {
  title: string;
  description: string;
  children: ReactNode;
  footer: ReactNode;
  registration?: boolean;
}) {
  return (
    <main
      className={`fh-auth${registration ? " fh-auth-registration" : ""}`}
      aria-labelledby="auth-title"
    >
      <div className="auth-content">
        <div className="auth-intro">
          <p className="auth-kicker">YOUR TEAMS. YOUR GAME.</p>
          <h1 id="auth-title">{title}</h1>
          <p>{description}</p>
        </div>
        <section
          className="auth-card"
          aria-label={registration ? "Registration form" : "Login form"}
        >
          {children}
          <div className="auth-switch">{footer}</div>
        </section>
        <p className="auth-responsible">
          Gamble responsibly. Must be 21+ to participate.
        </p>
      </div>
    </main>
  );
}

type FieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "name"> & {
  name: string;
  label: string;
  error?: string;
  hint?: string;
  onToggleVisibility?: () => void;
  passwordVisible?: boolean;
};

export function AuthField({
  name,
  label,
  error,
  hint,
  onToggleVisibility,
  passwordVisible,
  ...input
}: FieldProps) {
  const describedBy =
    [hint && `${name}-hint`, error && `${name}-error`]
      .filter(Boolean)
      .join(" ") || undefined;
  return (
    <div className="auth-field">
      <label htmlFor={name}>{label}</label>
      <div
        className={`auth-input-wrap${onToggleVisibility ? " auth-password" : ""}`}
      >
        <input
          {...input}
          id={name}
          name={name}
          aria-invalid={!!error}
          aria-describedby={describedBy}
        />
        {onToggleVisibility && (
          <button
            type="button"
            className="auth-reveal"
            onClick={onToggleVisibility}
            disabled={input.disabled}
            aria-label={`${passwordVisible ? "Hide" : "Show"} ${name === "confirmPassword" ? "confirm password" : "password"}`}
            aria-pressed={!!passwordVisible}
          >
            {passwordVisible ? (
              <EyeOff size={18} aria-hidden="true" />
            ) : (
              <Eye size={18} aria-hidden="true" />
            )}
          </button>
        )}
      </div>
      {hint && (
        <p className="auth-hint" id={`${name}-hint`}>
          {hint}
        </p>
      )}
      {error && (
        <p className="auth-error" id={`${name}-error`} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function AuthSubmit({
  pending,
  label,
  pendingLabel,
}: {
  pending: boolean;
  label: string;
  pendingLabel: string;
}) {
  return (
    <button className="auth-submit" type="submit" disabled={pending}>
      <span>{pending ? pendingLabel : label}</span>
      {pending ? (
        <LoaderCircle className="auth-spinner" size={18} aria-hidden="true" />
      ) : (
        <ArrowRight size={18} aria-hidden="true" />
      )}
    </button>
  );
}
