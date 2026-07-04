import { formatLastUpdated } from "../lib/format";
import type { TrendSource } from "../types";

import { FreshnessBadge, SourceBadge } from "./SourceBadge";
import { TrendCard } from "./TrendCard";

type TrendSourceGroupProps = {
  source: TrendSource;
  itemLimit?: number;
};

export function TrendSourceGroup({ source, itemLimit }: TrendSourceGroupProps) {
  const items = typeof itemLimit === "number" ? source.items.slice(0, itemLimit) : source.items;

  return (
    <div className="source-group">
      <div className="source-meta">
        <span>
          Source: <SourceBadge source={source.source} />
        </span>
        <span aria-hidden="true">/</span>
        <FreshnessBadge status={source.status} />
        <span aria-hidden="true">/</span>
        <span>Last updated {formatLastUpdated(source.last_updated)}</span>
      </div>

      {items.length > 0 ? (
        <div className="trend-list">
          {items.map((item) => (
            <TrendCard item={item} key={`${source.source}-${item.rank}-${item.url}`} />
          ))}
        </div>
      ) : (
        <div className="empty-state">No trend items are available for this source yet.</div>
      )}
    </div>
  );
}
