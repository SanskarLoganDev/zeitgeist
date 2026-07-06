import type { TrendItem } from "../types";

import { formatSourceShort } from "../lib/format";

import { SourceBadge } from "./SourceBadge";

type TrendCardProps = {
  item: TrendItem;
  displayRank?: number;
  showSource?: boolean;
  showScoreSource?: boolean;
};

export function TrendCard({
  item,
  displayRank,
  showSource = false,
  showScoreSource = false
}: TrendCardProps) {
  const primaryUrl = item.external_url ?? item.url;
  const sourceSuffix = showScoreSource ? ` · ${formatSourceShort(item.source)}` : "";

  return (
    <article className="trend-card">
      <span className="rank">{displayRank ?? item.rank}</span>
      <div>
        <h3 className="trend-title">
          <a href={primaryUrl} rel="noreferrer" target="_blank">
            {item.title}
          </a>
        </h3>
        <div className="trend-links">
          {showSource ? (
            <span className="trend-source">
              <SourceBadge source={item.source} />
            </span>
          ) : null}
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
        {sourceSuffix}
      </span>
    </article>
  );
}
