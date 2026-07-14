"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { getAuthConfig, requestPasswordReset, resetPassword } from "../lib/auth";

export function ForgotPasswordForm() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [defaultResendCooldownSeconds, setDefaultResendCooldownSeconds] = useState(60);
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resendCooldownRemaining, setResendCooldownRemaining] = useState(0);
  const [hasRequestedCode, setHasRequestedCode] = useState(false);
  const [isRequestingCode, setIsRequestingCode] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  useEffect(() => {
    let isMounted = true;

    getAuthConfig()
      .then((config) => {
        if (!isMounted) {
          return;
        }
        setDefaultResendCooldownSeconds(
          config.email_verification.resend_cooldown_seconds
        );
      })
      .catch(() => {
        // The server still enforces cooldown. Keep the local fallback if config fails.
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (resendCooldownRemaining <= 0) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setResendCooldownRemaining((currentValue) => Math.max(currentValue - 1, 0));
    }, 1000);

    return () => window.clearInterval(timer);
  }, [resendCooldownRemaining]);

  async function handleRequestCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsRequestingCode(true);

    try {
      const response = await requestPasswordReset({ email });
      setMessage(response.detail);
      setHasRequestedCode(true);
      setResendCooldownRemaining(
        response.resend_cooldown_seconds ?? defaultResendCooldownSeconds
      );
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not send reset code.");
    } finally {
      setIsRequestingCode(false);
    }
  }

  async function handleResetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsResetting(true);

    try {
      const response = await resetPassword({
        code,
        email,
        new_password: newPassword
      });
      setMessage(response.detail);
      window.setTimeout(() => {
        router.push("/login");
      }, 900);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not reset password.");
    } finally {
      setIsResetting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-form-shell">
        <p className="eyebrow">Account</p>
        <h1>Reset password</h1>
        <p className="lede">
          Enter your account email and we will send a 6-digit reset code.
        </p>

        <form className="auth-form" onSubmit={handleRequestCode}>
          <label className="field">
            <span>Email</span>
            <input
              autoComplete="email"
              className="input"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>

          <button
            className="secondary-button auth-inline-button"
            disabled={
              isRequestingCode || email.length === 0 || resendCooldownRemaining > 0
            }
            type="submit"
          >
            {resendCooldownRemaining > 0
              ? `Send again in ${resendCooldownRemaining}s`
              : isRequestingCode
                ? "Sending..."
                : hasRequestedCode
                  ? "Send code again"
                  : "Send reset code"}
          </button>
        </form>

        {hasRequestedCode ? (
          <form className="auth-form" onSubmit={handleResetPassword}>
            <label className="field">
              <span>Reset code</span>
              <input
                autoComplete="one-time-code"
                className="input"
                inputMode="numeric"
                maxLength={6}
                minLength={6}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
                pattern="[0-9]{6}"
                required
                type="text"
                value={code}
              />
            </label>

            <label className="field">
              <span>New password</span>
              <input
                autoComplete="new-password"
                className="input"
                minLength={8}
                onChange={(event) => setNewPassword(event.target.value)}
                required
                type="password"
                value={newPassword}
              />
            </label>

            <button className="primary-button auth-inline-button" disabled={isResetting} type="submit">
              {isResetting ? "Updating..." : "Update password"}
            </button>
          </form>
        ) : null}

        {error !== null ? <p className="error-message">{error}</p> : null}
        {message !== null ? <p className="success-message">{message}</p> : null}

        <div className="button-row auth-footer-actions">
          <Link className="secondary-button" href="/login">
            Back to sign in
          </Link>
        </div>
      </section>
    </main>
  );
}
