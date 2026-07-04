import { notFound } from "next/navigation";

import { CategorySection } from "../../../components/CategorySection";
import { CategorySidebar } from "../../../components/CategorySidebar";
import { getCategories, getCategoryTrends } from "../../../lib/api";

export const dynamic = "force-dynamic";

type CategoryPageProps = {
  params: {
    slug: string;
  };
};

export default async function CategoryPage({ params }: CategoryPageProps) {
  const categories = await getCategories();
  const knownCategory = categories.find((category) => category.slug === params.slug);

  if (knownCategory === undefined) {
    notFound();
  }

  const category = await getCategoryTrends(params.slug, 20);

  return (
    <main className="app-shell">
      <CategorySidebar activeSlug={params.slug} categories={categories} />
      <div className="content">
        <header className="page-header">
          <div>
            <p className="eyebrow">Category detail</p>
            <h1>{category.name}</h1>
            <p className="lede">
              The latest ranked items for this category from verified sources. Phase 1 shows the
              newest stored snapshot.
            </p>
          </div>
        </header>

        <div className="dashboard-grid">
          <CategorySection category={category} />
        </div>
      </div>
    </main>
  );
}
