import type { FreshnessStatus } from "../types";

const SOURCE_LABELS: Record<string, string> = {
  devto: "DEV",
  football_data: "Football-Data",
  hackernews: "Hacker News",
  nytimes: "New York Times",
  rawg: "RAWG"
};

const SOURCE_SHORT_LABELS: Record<string, string> = {
  devto: "DEV",
  football_data: "Football",
  hackernews: "HN",
  nytimes: "NYT",
  rawg: "RAWG"
};

export function formatSource(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}

export function formatSourceShort(source: string): string {
  return SOURCE_SHORT_LABELS[source] ?? formatSource(source);
}

export function formatLastUpdated(value: string | null): string {
  if (value === null) {
    return "No successful run yet";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown update time";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC"
  }).format(date);
}

export function freshnessLabel(status: FreshnessStatus): string {
  if (status === "fresh") {
    return "Fresh";
  }
  if (status === "stale") {
    return "Stale";
  }
  return "Missing";
}
