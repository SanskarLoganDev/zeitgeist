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
  source: string;
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

export type CategorySourceStatus = {
  source: string;
  last_updated: string | null;
  status: FreshnessStatus;
};

export type CategoryTrendsPagination = {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  max_items: number;
};

export type CategoryTrendsResponse = {
  id: number;
  name: string;
  slug: string;
  icon: string;
  sources: CategorySourceStatus[];
  items: TrendItem[];
  pagination: CategoryTrendsPagination;
};

export type User = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
};

export type AuthState = {
  authenticated: boolean;
  user: User | null;
};

export type CategoryPreferenceState = {
  can_save: boolean;
  selected_slugs: string[];
};
