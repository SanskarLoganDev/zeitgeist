import type { Category, CategoryTrendsResponse, DashboardResponse } from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

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

export function getCategoryTrends(slug: string, limit = 20): Promise<CategoryTrendsResponse> {
  return fetchJson<CategoryTrendsResponse>(`/categories/${slug}/trends/?limit=${limit}`, {
    next: { revalidate: 60 }
  });
}
