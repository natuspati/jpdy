import { type ReactNode } from 'react';

import Badge from '@/components/ui/Badge';
import Card from '@/components/ui/Card';
import Spinner from '@/components/ui/Spinner';
import { useServerStatus } from '@/hooks/useAdmin';
import type { HealthStatusEnum } from '@/schemas';
import { formatBytes, formatDuration } from '@/utils/format';
import AdminSection from './AdminSection';

const statusTone = { ok: 'success', degraded: 'warning', down: 'danger' } as const;

const StatusBadge = ({ status }: { status: HealthStatusEnum }) => (
  <Badge tone={statusTone[status]}>{status}</Badge>
);

const Row = ({ label, value }: { label: string; value: ReactNode }) => (
  <div className="flex justify-between gap-3">
    <dt className="text-slate-400">{label}</dt>
    <dd className="text-right font-medium tabular-nums text-slate-100">{value ?? '-'}</dd>
  </div>
);

const Panel = ({
  title,
  status,
  error,
  children,
}: {
  title: string;
  status: HealthStatusEnum;
  error: string | null;
  children: ReactNode;
}) => (
  <Card className="space-y-2 p-3">
    <div className="flex items-center justify-between">
      <h3 className="font-semibold text-slate-100">{title}</h3>
      <StatusBadge status={status} />
    </div>
    {error ? <p className="break-words text-xs text-rose-400">{error}</p> : null}
    <dl className="space-y-1 text-sm">{children}</dl>
  </Card>
);

const orNull = <T, R>(value: T | null, format: (value: T) => R): R | null =>
  value === null ? null : format(value);

const ServerManagement = () => {
  const { data, isLoading, isError } = useServerStatus();

  return (
    <AdminSection title="Server" actions={data ? <StatusBadge status={data.status} /> : undefined}>
      {isLoading ? (
        <div className="flex justify-center p-4">
          <Spinner />
        </div>
      ) : isError || !data ? (
        <p className="p-4 text-rose-400">Server status is unavailable.</p>
      ) : (
        <div className="space-y-3 p-3">
          <Panel title="Redis" status={data.redis.status} error={data.redis.error}>
            <Row label="Ping" value={orNull(data.redis.ping_ms, (ms) => `${ms} ms`)} />
            <Row label="Memory" value={orNull(data.redis.used_memory, formatBytes)} />
            <Row
              label="Max memory"
              value={orNull(data.redis.maxmemory, (bytes) =>
                bytes === 0 ? 'unlimited' : formatBytes(bytes),
              )}
            />
            <Row label="Clients" value={data.redis.connected_clients} />
            <Row label="Ops/s" value={data.redis.ops_per_sec} />
            <Row label="Uptime" value={orNull(data.redis.uptime_seconds, formatDuration)} />
            <Row label="Evicted keys" value={data.redis.evicted_keys} />
            <Row label="Rejected connections" value={data.redis.rejected_connections} />
            <Row label="Game state keys" value={data.redis.game_state_keys} />
          </Panel>
          <Panel title="Database" status={data.database.status} error={data.database.error}>
            <Row label="Engine" value={data.database.dialect} />
            <Row label="Ping" value={orNull(data.database.ping_ms, (ms) => `${ms} ms`)} />
            <Row
              label="Pool"
              value={orNull(
                data.database.pool_size,
                (size) => `${data.database.pool_checked_out ?? 0} / ${size} in use`,
              )}
            />
            <Row label="Pool overflow" value={data.database.pool_overflow} />
            <Row label="Users" value={data.database.user_count} />
            <Row label="Lobbies" value={data.database.lobby_count} />
            <Row label="Categories" value={data.database.category_count} />
            <Row label="Size" value={orNull(data.database.size_bytes, formatBytes)} />
            <Row label="Connections" value={data.database.active_connections} />
          </Panel>
          <Panel title="Backend" status={data.backend.status} error={data.backend.error}>
            <Row label="Instances" value={data.backend.instances.length} />
            <Row label="Connected sockets" value={data.backend.connected_sockets} />
            <Row label="Live games" value={data.backend.live_games} />
            {data.backend.instances.map((instance) => (
              <div
                key={instance.id}
                className="mt-2 space-y-1 rounded-md border border-slate-800 p-2 text-xs"
              >
                <Row label="Instance" value={instance.id.slice(0, 8)} />
                <Row label="Host" value={instance.hostname} />
                <Row label="Version" value={instance.version} />
                <Row
                  label="Uptime"
                  value={formatDuration(
                    (Date.now() - new Date(instance.started_at).getTime()) / 1000,
                  )}
                />
                <Row label="Peak memory" value={formatBytes(instance.rss_bytes)} />
              </div>
            ))}
          </Panel>
        </div>
      )}
    </AdminSection>
  );
};

export default ServerManagement;
