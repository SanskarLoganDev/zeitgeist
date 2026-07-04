"use client";

import Link from "next/link";

import { logout } from "../lib/auth";
import type { AuthState } from "../types";

type AuthPanelProps = {
  auth: AuthState | null;
  isLoading: boolean;
  onAuthChange: (auth: AuthState) => void;
};

export function AuthPanel({ auth, isLoading, onAuthChange }: AuthPanelProps) {
  async function handleLogout() {
    const nextAuth = await logout();
    onAuthChange(nextAuth);
  }

  if (isLoading) {
    return (
      <section className="auth-panel" aria-label="Account">
        <span className="muted">Checking account...</span>
      </section>
    );
  }

  if (auth?.authenticated === true && auth.user !== null) {
    return (
      <section className="auth-panel" aria-label="Account">
        <div>
          <p className="panel-label">Signed in</p>
          <p className="account-email">{auth.user.email}</p>
        </div>
        <button className="secondary-button" onClick={handleLogout} type="button">
          Sign out
        </button>
      </section>
    );
  }

  return (
    <section className="auth-panel" aria-label="Account">
      <div>
        <p className="panel-label">Guest mode</p>
        <p className="muted">Choose categories here. Sign in to keep them.</p>
      </div>
      <div className="auth-actions">
        <Link className="primary-button" href="/login">
          Sign in
        </Link>
        <Link className="secondary-button" href="/signup">
          Create account
        </Link>
      </div>
    </section>
  );
}
