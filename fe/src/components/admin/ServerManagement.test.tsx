import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { ServerStatus } from '@/schemas';
import ServerManagement from './ServerManagement';

const { server } = vi.hoisted(() => ({
  server: { data: undefined as ServerStatus | undefined, isLoading: false, isError: false },
}));
vi.mock('@/hooks/useAdmin', () => ({ useServerStatus: () => server }));

const status = (overrides: Partial<ServerStatus> = {}): ServerStatus => ({
  status: 'ok',
  redis: {
    status: 'ok',
    error: null,
    ping_ms: 0.4,
    used_memory: 2 * 1024 * 1024,
    maxmemory: 0,
    connected_clients: 3,
    ops_per_sec: 12,
    uptime_seconds: 90_000,
    evicted_keys: 0,
    rejected_connections: 0,
    game_state_keys: 4,
  },
  database: {
    status: 'ok',
    error: null,
    dialect: 'postgresql',
    ping_ms: 1.2,
    pool_size: 5,
    pool_checked_out: 1,
    pool_overflow: 0,
    user_count: 10,
    lobby_count: 7,
    category_count: 9,
    size_bytes: 8 * 1024 * 1024,
    active_connections: 6,
  },
  backend: {
    status: 'ok',
    error: null,
    instances: [
      {
        id: 'aaaaaaaabbbbbbbb',
        hostname: 'api-1',
        version: '0.2.0',
        started_at: new Date(Date.now() - 3_600_000).toISOString(),
        rss_bytes: 100 * 1024 * 1024,
      },
      {
        id: 'ccccccccdddddddd',
        hostname: 'api-2',
        version: '0.2.0',
        started_at: new Date(Date.now() - 60_000).toISOString(),
        rss_bytes: 90 * 1024 * 1024,
      },
    ],
    connected_sockets: 5,
    live_games: 2,
  },
  ...overrides,
});

describe('ServerManagement', () => {
  it('shows each dependency and every backend instance', () => {
    server.data = status();
    render(<ServerManagement />);

    expect(screen.getByRole('heading', { name: 'Redis' })).toBeInTheDocument();
    expect(screen.getByText('2.0 MB')).toBeInTheDocument();
    expect(screen.getByText('unlimited')).toBeInTheDocument();
    expect(screen.getByText('1d 1h')).toBeInTheDocument();
    expect(screen.getByText('postgresql')).toBeInTheDocument();
    expect(screen.getByText('aaaaaaaa')).toBeInTheDocument();
    expect(screen.getByText('cccccccc')).toBeInTheDocument();
    expect(screen.getByText('api-2')).toBeInTheDocument();
  });

  it('shows a dead dependency as down with its error instead of failing', () => {
    server.data = status({
      status: 'degraded',
      redis: {
        ...status().redis,
        status: 'down',
        error: 'ConnectionError: refused',
        ping_ms: null,
        used_memory: null,
        game_state_keys: null,
      },
    });
    render(<ServerManagement />);

    const redis = screen.getByRole('heading', { name: 'Redis' }).closest('div');
    if (!redis?.parentElement) throw new Error('Redis panel missing');
    expect(within(redis).getByText('down')).toBeInTheDocument();
    expect(within(redis.parentElement).getByText('ConnectionError: refused')).toBeInTheDocument();
    expect(screen.getByText('degraded')).toBeInTheDocument();
    expect(screen.getByText('postgresql')).toBeInTheDocument();
  });
});
