import type { AuthState, CategoryPreferenceState } from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type AuthInput = {
  email: string;
  password: string;
};

function readCookie(name: string): string | null {
  const cookies = document.cookie.split("; ");
  const cookie = cookies.find((item) => item.startsWith(`${name}=`));
  if (cookie === undefined) {
    return null;
  }

  return decodeURIComponent(cookie.split("=").slice(1).join("="));
}

async function ensureSecurityToken(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/auth/csrf/`, {
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error("Could not prepare secure request.");
  }

  const token = readCookie("csrftoken");
  if (token === null) {
    throw new Error("Security token cookie was not set.");
  }

  return token;
}

async function postJson<T>(path: string, body: object = {}): Promise<T> {
  const token = await ensureSecurityToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: JSON.stringify(body),
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": token
    },
    method: "POST"
  });

  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(error?.detail ?? "Request failed.");
  }

  return response.json() as Promise<T>;
}

async function patchJson<T>(path: string, body: object): Promise<T> {
  const token = await ensureSecurityToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: JSON.stringify(body),
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": token
    },
    method: "PATCH"
  });

  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(error?.detail ?? "Request failed.");
  }

  return response.json() as Promise<T>;
}

export async function getCurrentUser(): Promise<AuthState> {
  const response = await fetch(`${API_BASE_URL}/auth/me/`, {
    credentials: "include"
  });
  if (!response.ok) {
    return { authenticated: false, user: null };
  }

  return response.json() as Promise<AuthState>;
}

export function register(input: AuthInput): Promise<AuthState> {
  return postJson<AuthState>("/auth/register/", input);
}

export function login(input: AuthInput): Promise<AuthState> {
  return postJson<AuthState>("/auth/login/", input);
}

export function logout(): Promise<AuthState> {
  return postJson<AuthState>("/auth/logout/");
}

export async function getSavedPreferences(): Promise<CategoryPreferenceState> {
  const response = await fetch(`${API_BASE_URL}/categories/preferences/`, {
    credentials: "include"
  });
  if (!response.ok) {
    return { can_save: false, selected_slugs: [] };
  }

  return response.json() as Promise<CategoryPreferenceState>;
}

export function savePreferences(selectedSlugs: string[]): Promise<CategoryPreferenceState> {
  return patchJson<CategoryPreferenceState>("/categories/preferences/", {
    selected_slugs: selectedSlugs
  });
}
