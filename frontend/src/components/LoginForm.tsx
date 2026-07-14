"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { FormEvent } from "react";

import { login, register } from "../lib/auth";

type Mode = "login" | "register";

type LoginFormProps = {
  mode: Mode;
};

export function LoginForm({ mode }: LoginFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (mode === "register") {
        const response = await register({ email, password });
        if ("verification_required" in response && response.verification_required) {
          const params = new URLSearchParams({
            email: response.email,
            resendCooldown: String(response.resend_cooldown_seconds)
          });
          router.push(`/verify-email?${params.toString()}`);
          return;
        }
      } else {
        await login({ email, password });
      }
      router.push("/");
      router.refresh();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Sign in failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-form-shell">
        <p className="eyebrow">Account</p>
        <h1>{mode === "login" ? "Sign in" : "Create account"}</h1>
        <p className="lede">
          Save your category choices and restore them on another browser or device.
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
            <span>Password</span>
            <input
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              className="input"
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error !== null ? <p className="error-message">{error}</p> : null}

          <div className="button-row">
            <button className="primary-button" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Working..." : mode === "login" ? "Sign in" : "Create account"}
            </button>
            <Link className="secondary-button" href={mode === "login" ? "/signup" : "/login"}>
              {mode === "login" ? "Create account" : "Use existing account"}
            </Link>
          </div>
        </form>
      </section>
    </main>
  );
}
