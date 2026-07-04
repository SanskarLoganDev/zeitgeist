import type { TrendItem } from "../types";

type TrendCardProps = {
  item: TrendItem;
};

export function TrendCard({ item }: TrendCardProps) {
  const primaryUrl = item.external_url ?? item.url;

  return (
    <article className="trend-card">
      <span className="rank">{item.rank}</span>
      <div>
        <h3 className="trend-title">
          <a href={primaryUrl} rel="noreferrer" target="_blank">
            {item.title}
          </a>
        </h3>
        <div className="trend-links">
          {item.external_url !== null ? (
            <a className="trend-link" href={item.external_url} rel="noreferrer" target="_blank">
              Original
            </a>
          ) : null}
          <a className="trend-link" href={item.url} rel="noreferrer" target="_blank">
            Discussion
          </a>
        </div>
      </div>
      <span className="score">
        {item.score.toLocaleString()} {item.score_label}
      </span>
    </article>
  );
}
