"use client";

import type { DashboardCategory } from "../types";

type SaveState = "idle" | "saving" | "saved" | "error";

type PreferencePanelProps = {
  canSave: boolean;
  categories: DashboardCategory[];
  onSave: () => Promise<void>;
  onSelectionChange: (selectedSlugs: string[]) => void;
  saveState: SaveState;
  selectedSlugs: string[];
};

export function PreferencePanel({
  canSave,
  categories,
  onSave,
  onSelectionChange,
  saveState,
  selectedSlugs
}: PreferencePanelProps) {
  function toggleCategory(slug: string) {
    if (selectedSlugs.includes(slug)) {
      onSelectionChange(selectedSlugs.filter((selectedSlug) => selectedSlug !== slug));
      return;
    }

    onSelectionChange([...selectedSlugs, slug]);
  }

  return (
    <section className="preference-panel" aria-label="Category preferences">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Preferences</p>
          <h2>Choose what appears on your dashboard</h2>
        </div>
        <button
          className="primary-button"
          disabled={!canSave || saveState === "saving"}
          onClick={onSave}
          type="button"
        >
          {saveState === "saving" ? "Saving..." : "Save"}
        </button>
      </div>

      <div className="preference-list">
        {categories.map((category) => (
          <label className="preference-item" key={category.slug}>
            <input
              checked={selectedSlugs.includes(category.slug)}
              onChange={() => toggleCategory(category.slug)}
              type="checkbox"
            />
            <span>{category.name}</span>
          </label>
        ))}
      </div>

      {!canSave ? (
        <p className="notice">Your choices stay in this browser until you sign in.</p>
      ) : null}
      {saveState === "saved" ? <p className="success-message">Preferences saved.</p> : null}
      {saveState === "error" ? (
        <p className="error-message">Could not save preferences. Please try again.</p>
      ) : null}
    </section>
  );
}
