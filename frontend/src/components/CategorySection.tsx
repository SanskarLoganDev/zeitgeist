import Link from "next/link";

import type { DashboardCategory } from "../types";

import { SummaryText } from "./SummaryText";
import { TrendSourceGroup } from "./TrendSourceGroup";

type CategorySectionProps = {
  category: DashboardCategory;
  itemLimit?: number;
  showViewAll?: boolean;
};

export function CategorySection({
  category,
  itemLimit,
  showViewAll = false
}: CategorySectionProps) {
  return (
    <section className="category-section">
      <header className="category-section-header">
        <div className="category-section-title">
          <h2>{category.name}</h2>
        </div>
        {showViewAll ? (
          <Link className="trend-link" href={`/category/${category.slug}`}>
            View full list
          </Link>
        ) : null}
      </header>

      {category.ai_summary !== null ? (
        <SummaryText
          className="category-section-summary"
          text={category.ai_summary.summary_text}
        />
      ) : null}

      {category.sources.length > 0 ? (
        category.sources.map((source) => (
          <TrendSourceGroup itemLimit={itemLimit} key={source.source} source={source} />
        ))
      ) : (
        <div className="source-group">
          <div className="empty-state">No verified source is active for this category yet.</div>
        </div>
      )}
    </section>
  );
}
