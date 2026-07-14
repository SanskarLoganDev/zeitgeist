"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { getAuthConfig, resendVerification, verifyEmail } from "../lib/auth";

type VerifyEmailFormProps = {
  initialEmail: string;
  initialResendCooldownSeconds: number;
};

export function VerifyEmailForm({
  initialEmail,
  initialResendCooldownSeconds
}: VerifyEmailFormProps) {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [defaultResendCooldownSeconds, setDefaultResendCooldownSeconds] = useState(
    initialResendCooldownSeconds
  );
  const [email, setEmail] = useState(initialEmail);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [resendCooldownRemaining, setResendCooldownRemaining] = useState(
    initialResendCooldownSeconds
  );
  const [isResending, setIsResending] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

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
        // The server still enforces cooldown. Keep the value from registration if config fails.
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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsSubmitting(true);

    try {
      await verifyEmail({ email, code });
      router.push("/");
      router.refresh();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Verification failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleResend() {
    setError(null);
    setMessage(null);
    setIsResending(true);

    try {
      const response = await resendVerification({ email });
      setMessage(response.detail);
      setResendCooldownRemaining(response.resend_cooldown_seconds);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not resend code.");
      setResendCooldownRemaining(defaultResendCooldownSeconds);
    } finally {
      setIsResending(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-form-shell">
        <p className="eyebrow">Account</p>
        <h1>Verify email</h1>
        <p className="lede">
          Enter the 6-digit code sent to your email address.
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
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

          <label className="field">
            <span>Verification code</span>
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

          {error !== null ? <p className="error-message">{error}</p> : null}
          {message !== null ? <p className="success-message">{message}</p> : null}

          <div className="button-row">
            <button className="primary-button" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Verifying..." : "Verify email"}
            </button>
            <button
              className="secondary-button"
              disabled={isResending || email.length === 0 || resendCooldownRemaining > 0}
              onClick={handleResend}
              type="button"
            >
              {resendCooldownRemaining > 0
                ? `Resend in ${resendCooldownRemaining}s`
                : isResending
                  ? "Sending..."
                  : "Resend code"}
            </button>
            <Link className="secondary-button" href="/login">
              Back to sign in
            </Link>
          </div>
        </form>
      </section>
    </main>
  );
}
