import { notFound } from "next/navigation";
import Link from "next/link";

import { CategorySidebar } from "../../../components/CategorySidebar";
import { SourceBadge } from "../../../components/SourceBadge";
import { SummaryText } from "../../../components/SummaryText";
import { TrendCard } from "../../../components/TrendCard";
import { getCategories, getCategoryTrends } from "../../../lib/api";
import { formatLastUpdated } from "../../../lib/format";

export const dynamic = "force-dynamic";

type CategoryPageProps = {
  params: Promise<{
    slug: string;
  }>;
  searchParams?: Promise<{
    page?: string | string[];
    source?: string | string[];
  }>;
};

export default async function CategoryPage({ params, searchParams }: CategoryPageProps) {
  const { slug } = await params;
  const resolvedSearchParams = searchParams === undefined ? undefined : await searchParams;
  const categories = await getCategories();
  const knownCategory = categories.find((category) => category.slug === slug);

  if (knownCategory === undefined) {
    notFound();
  }

  const page = parsePage(resolvedSearchParams?.page);
  const selectedSource = parseSource(resolvedSearchParams?.source, knownCategory.sources);
  const category = await getCategoryTrends(slug, { page, pageSize: 10, source: selectedSource });
  const previousPage = category.pagination.page > 1 ? category.pagination.page - 1 : null;
  const nextPage =
    category.pagination.page < category.pagination.total_pages
      ? category.pagination.page + 1
      : null;
  const lastUpdated = latestLastUpdated(category.sources.map((source) => source.last_updated));

  return (
    <main className="app-shell">
      <CategorySidebar activeSlug={slug} categories={categories} />
      <div className="content">
        <header className="page-header">
          <div>
            <p className="eyebrow">Category detail</p>
            <h1>{category.name}</h1>
            <p className="lede">
              Top stored trends for this category, ranked across the latest verified source
              snapshots.
            </p>
          </div>
        </header>

        <div className="category-detail">
          {category.ai_summary ? (
            <section className="ai-summary">
              <div>
                <p className="panel-label">AI summary</p>
                <SummaryText
                  className="ai-summary-text"
                  text={category.ai_summary.summary_text}
                />
              </div>
              <p className="ai-summary-meta">
                {category.ai_summary.model_name} · {category.ai_summary.input_item_count} inputs ·{" "}
                {formatLastUpdated(category.ai_summary.generated_at)}
              </p>
            </section>
          ) : null}

          <div className="source-summary">
            <div className="source-summary-item">
              <span>Source:</span>
              <Link
                className={selectedSource === undefined ? "source-filter source-filter-active" : "source-filter"}
                href={`/category/${category.slug}`}
              >
                All
              </Link>
              {category.sources.map((source) => (
                <Link
                  className={
                    selectedSource === source.source
                      ? "source-filter source-filter-active"
                      : "source-filter"
                  }
                  href={`/category/${category.slug}?source=${source.source}`}
                  key={source.source}
                >
                  <SourceBadge source={source.source} />
                </Link>
              ))}
              <span className="source-summary-updated">
                Last updated {formatLastUpdated(lastUpdated)}
              </span>
            </div>
          </div>

          {category.items.length > 0 ? (
            <div className="trend-list category-detail-list">
              {category.items.map((item, index) => (
                <TrendCard
                  displayRank={(category.pagination.page - 1) * category.pagination.page_size + index + 1}
                  item={item}
                  key={`${item.source}-${item.rank}-${item.url}`}
                  showScoreSource
                />
              ))}
            </div>
          ) : (
            <div className="empty-state">No trend items are available for this category yet.</div>
          )}

          <nav aria-label="Category trend pages" className="pagination-bar">
            {previousPage === null ? (
              <span className="pagination-button pagination-button-disabled">Previous</span>
            ) : (
              <Link className="pagination-button" href={categoryPageHref(category.slug, previousPage, selectedSource)}>
                Previous
              </Link>
            )}

            <span className="pagination-status">
              Page {category.pagination.page} of {Math.max(category.pagination.total_pages, 1)}
            </span>

            {nextPage === null ? (
              <span className="pagination-button pagination-button-disabled">Next</span>
            ) : (
              <Link className="pagination-button" href={categoryPageHref(category.slug, nextPage, selectedSource)}>
                Next
              </Link>
            )}
          </nav>
        </div>
      </div>
    </main>
  );
}

function parseSource(rawSource: string | string[] | undefined, validSources: string[]): string | undefined {
  const value = Array.isArray(rawSource) ? rawSource[0] : rawSource;

  if (value === undefined || !validSources.includes(value)) {
    return undefined;
  }

  return value;
}

function categoryPageHref(slug: string, page: number, source: string | undefined): string {
  const params = new URLSearchParams({ page: String(page) });

  if (source !== undefined) {
    params.set("source", source);
  }

  return `/category/${slug}?${params.toString()}`;
}

function latestLastUpdated(values: Array<string | null>): string | null {
  const timestamps = values
    .map((value) => (value === null ? Number.NaN : new Date(value).getTime()))
    .filter((value) => !Number.isNaN(value));

  if (timestamps.length === 0) {
    return null;
  }

  return new Date(Math.max(...timestamps)).toISOString();
}

function parsePage(rawPage: string | string[] | undefined): number {
  const value = Array.isArray(rawPage) ? rawPage[0] : rawPage;
  const parsed = Number(value);

  if (!Number.isInteger(parsed) || parsed < 1) {
    return 1;
  }

  return parsed;
}
