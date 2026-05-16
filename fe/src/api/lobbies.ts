import { z } from 'zod';

import {
  LobbyFilter,
  LobbyInDB,
  LobbyUpdate,
  LobbyWithCategories,
  PaginatedLobbies,
} from '@/schemas';
import { request } from './http';

export async function searchLobbies(filters: Partial<LobbyFilter>) {
  return request('/lobby', PaginatedLobbies, { search: filters });
}

export async function getLobby(id: number) {
  return request(`/lobby/${id}`, LobbyWithCategories);
}

export async function createLobby() {
  return request('/lobby', LobbyInDB, { method: 'POST' });
}

export async function updateLobby(id: number, payload: LobbyUpdate) {
  return request(`/lobby/${id}`, LobbyWithCategories, { method: 'PATCH', body: payload });
}

export async function deleteLobby(id: number) {
  return request(`/lobby/${id}`, z.void(), { method: 'DELETE' });
}
