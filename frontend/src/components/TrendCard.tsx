import type { TrendItem } from "../types";

import { formatScore, formatSourceShort } from "../lib/format";

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
  if (item.source === "football_data") {
    return <FootballMatchCard displayRank={displayRank} item={item} />;
  }
  if (item.source === "cricket_data") {
    return <CricketMatchCard displayRank={displayRank} item={item} />;
  }

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
        {formatScore(item.score)} {item.score_label}
        {sourceSuffix}
      </span>
    </article>
  );
}

function FootballMatchCard({ item, displayRank }: Pick<TrendCardProps, "item" | "displayRank">) {
  const metadata = item.metadata;
  const homeTeam = stringValue(metadata.home_team) ?? "Home";
  const awayTeam = stringValue(metadata.away_team) ?? "Away";
  const homeScore = numberValue(metadata.home_score);
  const awayScore = numberValue(metadata.away_score);
  const penaltyHomeScore = numberValue(metadata.penalty_home_score);
  const penaltyAwayScore = numberValue(metadata.penalty_away_score);
  const competitionName = stringValue(metadata.competition_name) ?? "Football";
  const statusLabel = stringValue(metadata.status_label) ?? item.score_label;
  const stageLabel = stringValue(metadata.stage_label);
  const utcDate = stringValue(metadata.utc_date);

  return (
    <article className="football-card">
      <div className="football-card-topline">
        <span>
          {competitionName}
          {utcDate !== undefined ? ` · ${formatMatchDate(utcDate)}` : ""}
        </span>
        <strong>{statusLabel}</strong>
      </div>
      <div className="football-card-scoreboard">
        <div className="football-team football-team-home">
          <span className="football-team-name">{homeTeam}</span>
        </div>
        <div className="football-score">
          <span>{homeScore ?? "-"}</span>
          <span aria-hidden="true">-</span>
          <span>{awayScore ?? "-"}</span>
        </div>
        <div className="football-team football-team-away">
          <span className="football-team-name">{awayTeam}</span>
        </div>
      </div>
      <div className="football-card-footer">
        {penaltyHomeScore !== undefined && penaltyAwayScore !== undefined ? (
          <span>
            Penalties: {penaltyHomeScore} - {penaltyAwayScore}
          </span>
        ) : null}
        {stageLabel !== undefined ? <span>{stageLabel}</span> : null}
      </div>
    </article>
  );
}

function CricketMatchCard({ item, displayRank }: Pick<TrendCardProps, "item" | "displayRank">) {
  const metadata = item.metadata;
  const teamA = stringValue(metadata.team_a) ?? firstTeam(metadata.teams) ?? "Team A";
  const teamB = stringValue(metadata.team_b) ?? secondTeam(metadata.teams) ?? "Team B";
  const matchType = stringValue(metadata.match_type)?.toUpperCase() ?? "Cricket";
  const venue = stringValue(metadata.venue);
  const statusLabel = stringValue(metadata.status_label) ?? item.score_label;
  const scoreText = stringValue(metadata.score_text);
  const dateTimeGmt = stringValue(metadata.date_time_gmt);

  return (
    <article className="football-card">
      <div className="football-card-topline">
        <span>
          #{displayRank ?? item.rank} · {matchType}
          {dateTimeGmt !== undefined ? ` · ${formatMatchDate(dateTimeGmt)}` : ""}
        </span>
        <strong>{statusLabel}</strong>
      </div>
      <div className="football-card-scoreboard">
        <div className="football-team football-team-home">
          <span className="football-team-name">{teamA}</span>
        </div>
        <div className="football-score football-score-compact">
          <span>vs</span>
        </div>
        <div className="football-team football-team-away">
          <span className="football-team-name">{teamB}</span>
        </div>
      </div>
      <div className="football-card-footer">
        {scoreText !== undefined ? <span>{scoreText}</span> : null}
        {venue !== undefined ? <span>{venue}</span> : null}
      </div>
    </article>
  );
}

function stringValue(value: unknown): string | undefined {
  if (typeof value !== "string" || value.trim().length === 0) {
    return undefined;
  }
  return value;
}

function numberValue(value: unknown): number | undefined {
  return typeof value === "number" ? value : undefined;
}

function firstTeam(value: unknown): string | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }
  return stringValue(value[0]);
}

function secondTeam(value: unknown): string | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }
  return stringValue(value[1]);
}

function formatMatchDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date TBA";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC"
  }).format(date);
}
