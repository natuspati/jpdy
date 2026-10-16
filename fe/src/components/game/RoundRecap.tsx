export interface RoundStanding {
  key: string | number;
  username: string;
  /** Cumulative score after the round. */
  score: number;
  /** Points earned during the round. */
  scoreDelta: number;
  isBanned?: boolean;
}

const formatDelta = (delta: number): string => (delta > 0 ? `+${delta}` : `${delta}`);

const compareStandings = (a: RoundStanding, b: RoundStanding): number =>
  b.score - a.score || a.username.localeCompare(b.username);

export const RoundStandings = ({ standings }: { standings: readonly RoundStanding[] }) => (
  <ol className="space-y-1">
    {[...standings].sort(compareStandings).map((standing, index) => (
      <li
        key={standing.key}
        className="flex items-center justify-between gap-2 rounded-md bg-slate-800/60 px-2 py-1.5"
      >
        <span className="flex items-center gap-2">
          <span className="w-6 text-right text-slate-400">{index + 1}.</span>
          <span>{standing.username}</span>
          {standing.isBanned ? <span className="text-xs text-rose-300">(banned)</span> : null}
        </span>
        <span className="flex items-baseline gap-2 tabular-nums">
          <span>{standing.score}</span>
          <span
            className={`w-16 text-right text-xs ${
              standing.scoreDelta < 0 ? 'text-rose-300' : 'text-emerald-300'
            }`}
          >
            {formatDelta(standing.scoreDelta)}
          </span>
        </span>
      </li>
    ))}
  </ol>
);

interface Props {
  roundNumber: number;
  categoryNames: readonly string[];
  standings: readonly RoundStanding[] | null;
}

/** One round's categories plus the standings after it (cumulative score and round delta). */
const RoundRecap = ({ roundNumber, categoryNames, standings }: Props) => (
  <section aria-label={`Round ${roundNumber}`} className="space-y-2">
    <h3 className="font-semibold text-amber-300">Round {roundNumber}</h3>
    <p className="text-sm text-slate-300">{categoryNames.join(' · ')}</p>
    {standings && standings.length > 0 ? <RoundStandings standings={standings} /> : null}
  </section>
);

export default RoundRecap;
