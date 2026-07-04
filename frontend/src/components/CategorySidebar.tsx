import Link from "next/link";

import type { Category, DashboardCategory } from "../types";

type CategorySidebarProps = {
  categories: Category[] | DashboardCategory[];
  activeSlug?: string;
};

export function CategorySidebar({ categories, activeSlug }: CategorySidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-title">Zeitgeist</span>
        <span className="brand-subtitle">Daily trend intelligence</span>
      </div>

      <p className="sidebar-label">Categories</p>
      <nav className="category-nav" aria-label="Categories">
        <Link
          className={`category-link ${activeSlug === undefined ? "category-link-active" : ""}`}
          href="/"
        >
          <span>Dashboard</span>
        </Link>
        {categories.map((category) => (
          <Link
            className={`category-link ${
              activeSlug === category.slug ? "category-link-active" : ""
            }`}
            href={`/category/${category.slug}`}
            key={category.slug}
          >
            <span>{category.name}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}
