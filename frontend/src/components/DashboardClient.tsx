"use client";

import { useEffect, useMemo, useState } from "react";

import { getCurrentUser, getSavedPreferences, savePreferences } from "../lib/auth";
import type { AuthState, DashboardResponse } from "../types";

import { AuthPanel } from "./AuthPanel";
import { CategorySection } from "./CategorySection";
import { CategorySidebar } from "./CategorySidebar";
import { PreferencePanel } from "./PreferencePanel";

const LOCAL_PREFERENCES_KEY = "zeitgeist:selected-categories";

type DashboardClientProps = {
  dashboard: DashboardResponse;
};

type SaveState = "idle" | "saving" | "saved" | "error";

function readLocalPreferences(): string[] | null {
  try {
    const rawValue = window.localStorage.getItem(LOCAL_PREFERENCES_KEY);
    if (rawValue === null) {
      return null;
    }

    const parsedValue = JSON.parse(rawValue) as unknown;
    if (!Array.isArray(parsedValue)) {
      return null;
    }

    return parsedValue.filter((value): value is string => typeof value === "string");
  } catch {
    return null;
  }
}

export function DashboardClient({ dashboard }: DashboardClientProps) {
  const allCategorySlugs = useMemo(
    () => dashboard.categories.map((category) => category.slug),
    [dashboard.categories]
  );
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [canSavePreferences, setCanSavePreferences] = useState(false);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [selectedSlugs, setSelectedSlugs] = useState<string[]>(allCategorySlugs);

  useEffect(() => {
    const localPreferences = readLocalPreferences();
    if (localPreferences === null) {
      return;
    }

    window.setTimeout(() => {
      setSelectedSlugs(localPreferences);
    }, 0);
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadAccountState() {
      const [nextAuth, savedPreferences] = await Promise.all([
        getCurrentUser(),
        getSavedPreferences()
      ]);

      if (!isMounted) {
        return;
      }

      setAuth(nextAuth);
      setCanSavePreferences(savedPreferences.can_save);
      if (savedPreferences.can_save && savedPreferences.selected_slugs.length > 0) {
        setSelectedSlugs(savedPreferences.selected_slugs);
      }
      setIsLoadingAuth(false);
    }

    loadAccountState().catch(() => {
      if (isMounted) {
        setAuth({ authenticated: false, user: null });
        setCanSavePreferences(false);
        setIsLoadingAuth(false);
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    window.localStorage.setItem(LOCAL_PREFERENCES_KEY, JSON.stringify(selectedSlugs));
  }, [selectedSlugs]);

  const sourceCount = dashboard.categories.reduce(
    (total, category) => total + category.sources.length,
    0
  );
  const selectedCategories = dashboard.categories.filter((category) =>
    selectedSlugs.includes(category.slug)
  );

  async function handleSavePreferences() {
    if (!canSavePreferences) {
      return;
    }

    setSaveState("saving");
    try {
      const savedPreferences = await savePreferences(selectedSlugs);
      setSelectedSlugs(savedPreferences.selected_slugs);
      setSaveState("saved");
    } catch {
      setSaveState("error");
    }
  }

  function handleAuthChange(nextAuth: AuthState) {
    setAuth(nextAuth);
    setCanSavePreferences(nextAuth.authenticated);
    setSaveState("idle");
  }

  function handleSelectionChange(nextSelectedSlugs: string[]) {
    setSelectedSlugs(nextSelectedSlugs);
    setSaveState("idle");
  }

  return (
    <main className="app-shell">
      <CategorySidebar categories={dashboard.categories} />
      <div className="content">
        <header className="page-header">
          <div>
            <p className="eyebrow">dashboard</p>
            <h1>Today&apos;s verified trends</h1>
            <p className="lede">
              Real trend data fetched by the ingestion job, stored in Postgres, and served through
              the Django backend.
            </p>
          </div>
          <div className="status-strip">
            <strong>{dashboard.categories.length}</strong>
            <span className="muted">categories</span>
            <strong>{sourceCount}</strong>
            <span className="muted">active sources</span>
          </div>
        </header>

        <div className="dashboard-tools">
          <AuthPanel auth={auth} isLoading={isLoadingAuth} onAuthChange={handleAuthChange} />
          <PreferencePanel
            canSave={canSavePreferences}
            categories={dashboard.categories}
            onSave={handleSavePreferences}
            onSelectionChange={handleSelectionChange}
            saveState={saveState}
            selectedSlugs={selectedSlugs}
          />
        </div>

        <div className="dashboard-grid">
          {selectedCategories.length > 0 ? (
            selectedCategories.map((category) => (
              <CategorySection
                category={category}
                itemLimit={5}
                key={category.slug}
                showViewAll
              />
            ))
          ) : (
            <div className="empty-state">Select at least one category to show trends.</div>
          )}
        </div>
      </div>
    </main>
  );
}
