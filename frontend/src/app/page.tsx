import { CategorySection } from "../components/CategorySection";
import { CategorySidebar } from "../components/CategorySidebar";
import { getDashboard } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const dashboard = await getDashboard();
  const sourceCount = dashboard.categories.reduce(
    (total, category) => total + category.sources.length,
    0
  );

  return (
    <main className="app-shell">
      <CategorySidebar categories={dashboard.categories} />
      <div className="content">
        <header className="page-header">
          <div>
            <p className="eyebrow">Phase 1 dashboard</p>
            <h1>Today&apos;s verified trends</h1>
            <p className="lede">
              Real trend data fetched by the ingestion job, stored in Postgres, and served through
              the Django API.
            </p>
          </div>
          <div className="status-strip">
            <strong>{dashboard.categories.length}</strong>
            <span className="muted">categories</span>
            <strong>{sourceCount}</strong>
            <span className="muted">active sources</span>
          </div>
        </header>

        <div className="dashboard-grid">
          {dashboard.categories.map((category) => (
            <CategorySection
              category={category}
              itemLimit={5}
              key={category.slug}
              showViewAll
            />
          ))}
        </div>
      </div>
    </main>
  );
}
