"use client";

type ErrorPageProps = {
  error: Error;
  reset: () => void;
};

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <main className="content">
      <p className="eyebrow">API unavailable</p>
      <h1>The dashboard could not load.</h1>
      <p className="lede">{error.message}</p>
      <button className="category-link" onClick={reset} type="button">
        Try again
      </button>
    </main>
  );
}
