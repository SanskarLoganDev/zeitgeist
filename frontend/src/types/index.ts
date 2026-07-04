export type FreshnessStatus = "fresh" | "stale" | "missing";

export type Category = {
  id: number;
  name: string;
  slug: string;
  icon: string;
  is_active: boolean;
  sources: string[];
};

export type TrendItem = {
  rank: number;
  title: string;
  url: string;
  external_url: string | null;
  score: number;
  score_label: string;
  ai_summary: string | null;
  sentiment: string | null;
};

export type TrendSource = {
  source: string;
  last_updated: string | null;
  status: FreshnessStatus;
  items: TrendItem[];
};

export type DashboardCategory = {
  id: number;
  name: string;
  slug: string;
  icon: string;
  sources: TrendSource[];
};

export type DashboardResponse = {
  categories: DashboardCategory[];
};

export type CategoryTrendsResponse = DashboardCategory;
