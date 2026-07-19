import type { Category, CategoryTrendsResponse, DashboardResponse } from "../types";

const API_BASE_URL =
  process.env.SERVER_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000/api/v1";

type FetchOptions = {
  next?: {
    revalidate?: number;
  };
};

async function fetchJson<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      Accept: "application/json"
    },
    ...options
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText} (${url})`);
  }

  return response.json() as Promise<T>;
}

export function getCategories(): Promise<Category[]> {
  return fetchJson<Category[]>("/categories/", { next: { revalidate: 60 } });
}

export function getDashboard(): Promise<DashboardResponse> {
  return fetchJson<DashboardResponse>("/dashboard/", { next: { revalidate: 60 } });
}

type CategoryTrendsOptions = {
  page?: number;
  pageSize?: number;
  source?: string;
};

export function getCategoryTrends(
  slug: string,
  { page = 1, pageSize = 10, source }: CategoryTrendsOptions = {}
): Promise<CategoryTrendsResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize)
  });
  if (source !== undefined) {
    params.set("source", source);
  }
  return fetchJson<CategoryTrendsResponse>(`/categories/${slug}/trends/?${params.toString()}`, {
    next: { revalidate: 60 }
  });
}
