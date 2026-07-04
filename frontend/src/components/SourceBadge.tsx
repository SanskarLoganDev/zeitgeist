import { formatSource, freshnessLabel } from "../lib/format";
import type { FreshnessStatus } from "../types";

type SourceBadgeProps = {
  source: string;
};

type FreshnessBadgeProps = {
  status: FreshnessStatus;
};

export function SourceBadge({ source }: SourceBadgeProps) {
  return <span>{formatSource(source)}</span>;
}

export function FreshnessBadge({ status }: FreshnessBadgeProps) {
  return <span>{freshnessLabel(status)}</span>;
}
