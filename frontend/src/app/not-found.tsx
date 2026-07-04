import Link from "next/link";

export default function NotFound() {
  return (
    <main className="content">
      <p className="eyebrow">Not found</p>
      <h1>That category does not exist.</h1>
      <p className="lede">The category may be inactive or not seeded yet.</p>
      <p>
        <Link className="trend-link" href="/">
          Back to dashboard
        </Link>
      </p>
    </main>
  );
}
