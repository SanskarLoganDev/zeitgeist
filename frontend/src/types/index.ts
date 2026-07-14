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
  metadata: Record<string, unknown>;
  ai_summary: string | null;
  sentiment: string | null;
};

export type TrendSource = {
  source: string;
  last_updated: string | null;
  status: FreshnessStatus;
  items: TrendItem[];
};

export type CategoryAISummary = {
  summary_text: string;
  model_name: string;
  input_item_count: number;
  generated_at: string;
};

export type DashboardCategory = {
  id: number;
  name: string;
  slug: string;
  icon: string;
  ai_summary: CategoryAISummary | null;
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
  ai_summary: CategoryAISummary | null;
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

export type VerificationRequiredState = {
  authenticated: false;
  user: null;
  verification_required: true;
  email: string;
  resend_cooldown_seconds: number;
  detail: string;
};

export type RegisterResponse = AuthState | VerificationRequiredState;

export type AuthConfig = {
  email_verification: {
    resend_cooldown_seconds: number;
  };
};

export type CategoryPreferenceState = {
  can_save: boolean;
  selected_slugs: string[];
};
